from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import (
    init_db,
    insert_telemetry,
    insert_event,
    get_latest_telemetry,
    get_recent_telemetry,
    get_recent_events,
    get_all_events,
    reset_shipment,
    get_all_active_events,
)

from event_detector import detect_events

from decision_engine import (
    calculate_event_risk,
    calculate_cumulative_risk,
    calculate_risk_breakdown,
)


app = FastAPI(title="ChainGuard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "https://chain-guard-ruddy.vercel.app"
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# REQUEST MODEL
# ======================================================

class SensorPayload(BaseModel):
    shipment_id: str
    temperature: float
    humidity: float
    acceleration: float
    tamper_status: int


# ======================================================
# STARTUP
# ======================================================

@app.on_event("startup")
def startup():

    init_db()


# ======================================================
# ROOT
# ======================================================

@app.get("/")
def root():

    return {
        "status": "online",
        "service": "ChainGuard API"
    }


# ======================================================
# HEALTH
# ======================================================

@app.get("/health")
def health():

    return {
        "status": "healthy"
    }

@app.get("/api/shipments/{shipment_id}/status")
def shipment_status(shipment_id: str):

    latest = get_latest_telemetry(shipment_id)

    if latest is None:
        return {
            "shipment_id": shipment_id,
            "device_status": "OFFLINE",
            "last_seen": None
        }

    timestamp = datetime.fromisoformat(
        latest["timestamp"]
    )

    seconds_since_last_seen = (
        datetime.utcnow() - timestamp
    ).total_seconds()

    device_status = (
        "ONLINE"
        if seconds_since_last_seen <= 15
        else "OFFLINE"
    )

    return {
        "shipment_id": shipment_id,
        "device_status": device_status,
        "last_seen": latest["timestamp"],
        "seconds_since_last_seen": round(
            seconds_since_last_seen,
            2
        )
    }
@app.delete("/api/shipments/{shipment_id}/reset")
def reset_shipment_data(shipment_id: str):
    reset_shipment(shipment_id)

    return {
        "status": "reset",
        "shipment_id": shipment_id,
        "message": "Shipment telemetry and event history cleared"
    }
# ======================================================
# TELEMETRY
# ======================================================

@app.post("/api/telemetry")
def receive_telemetry(data: SensorPayload):

    now = datetime.now(timezone.utc)

    # --------------------------------------------------
    # 1. Store raw telemetry
    # --------------------------------------------------

    telemetry_id = insert_telemetry(
        shipment_id=data.shipment_id,
        temperature=data.temperature,
        humidity=data.humidity,
        acceleration=data.acceleration,
        tamper_status=data.tamper_status
    )

    # --------------------------------------------------
    # 2. Detect events
    # --------------------------------------------------

    detected_events = detect_events(
        shipment_id=data.shipment_id,
        temperature=data.temperature,
        humidity=data.humidity,
        acceleration=data.acceleration,
        tamper_status=data.tamper_status,
        timestamp=now
    )

    # --------------------------------------------------
    # 3. Store events that were detected/ended
    # --------------------------------------------------

    stored_events = []

    for event in detected_events:

        event_type = event["event_type"]

        severity = event["severity"]

        # ----------------------------------------------
        # Shock
        # ----------------------------------------------

        if event_type == "shock":

            risk = calculate_event_risk(
                event_type="shock",
                severity=severity,
                frequency=1
            )

            event_id = insert_event(
                shipment_id=data.shipment_id,
                event_type=event_type,
                severity=severity,
                duration_seconds=0,
                frequency=1,
                risk_contribution=risk
            )

            stored_events.append({
                "id": event_id,
                "event_type": event_type,
                "severity": severity,
                "duration_seconds": 0,
                "frequency": 1,
                "risk_contribution": risk
            })

        # ----------------------------------------------
        # Environmental / tamper event ended
        # ----------------------------------------------

        elif event.get("event_status") == "ended":

            started_at = datetime.fromisoformat(
                event["started_at"]
            )

            ended_at = datetime.fromisoformat(
                event["ended_at"]
            )

            duration_seconds = max(
                (
                    ended_at - started_at
                ).total_seconds(),
                0
            )

            risk = calculate_event_risk(
                event_type=event_type,
                severity=severity,
                duration_seconds=duration_seconds
            )

            event_id = insert_event(
                shipment_id=data.shipment_id,
                event_type=event_type,
                severity=severity,
                duration_seconds=duration_seconds,
                frequency=1,
                risk_contribution=risk
            )

            stored_events.append({
                "id": event_id,
                "event_type": event_type,
                "severity": severity,
                "duration_seconds": round(
                    duration_seconds,
                    2
                ),
                "frequency": 1,
                "risk_contribution": round(
                    risk,
                    2
                )
            })

    # --------------------------------------------------
    # 4. Get complete shipment history
    # --------------------------------------------------

    completed_events = get_all_events(data.shipment_id)
    active_events = get_all_active_events(data.shipment_id)

    decision = calculate_cumulative_risk(
        completed_events=completed_events,
        active_events=active_events,
        now=now
    )

    risk_breakdown = calculate_risk_breakdown(
        completed_events=completed_events,
        active_events=active_events,
        now=now
    )

    # --------------------------------------------------
    # 6. Return result
    # --------------------------------------------------

    return {
    "status": "received",
    "shipment_id": data.shipment_id,
    "telemetry_id": telemetry_id,
    "integrity_score": decision["integrity_score"],
    "risk_score": decision["risk_score"],
    "decision": decision["status"],
    "shock_frequency": decision["shock_frequency"],
    "risk_breakdown": risk_breakdown,
    "events_detected": detected_events,
    "events_stored": stored_events
}


# ======================================================
# LATEST TELEMETRY
# ======================================================

@app.get(
    "/api/telemetry/latest/{shipment_id}"
)
def latest_telemetry(shipment_id: str):

    telemetry = get_latest_telemetry(
        shipment_id
    )

    if telemetry is None:

        return {
            "status": "not_found",
            "shipment_id": shipment_id
        }

    return telemetry


# ======================================================
# RECENT TELEMETRY
# ======================================================

@app.get(
    "/api/telemetry/{shipment_id}"
)
def recent_telemetry(shipment_id: str):

    telemetry = get_recent_telemetry(
        shipment_id
    )

    return {
        "shipment_id": shipment_id,
        "telemetry": telemetry
    }


# ======================================================
# EVENTS
# ======================================================

@app.get(
    "/api/events/{shipment_id}"
)
def recent_events(shipment_id: str):

    events = get_recent_events(
        shipment_id
    )

    return {
        "shipment_id": shipment_id,
        "events": events
    }


# ======================================================
# ACTIVE EVENTS
# ======================================================

@app.get(
    "/api/events/{shipment_id}/active"
)
def active_events(shipment_id: str):

    events = get_all_active_events(
        shipment_id
    )

    return {
        "shipment_id": shipment_id,
        "active_events": events
    }


# ======================================================
# SHIPMENT SUMMARY
# ======================================================

@app.get(
    "/api/shipments/{shipment_id}/summary"
)
def shipment_summary(shipment_id: str):

    latest = get_latest_telemetry(
        shipment_id
    )

    completed_events = get_all_events(
        shipment_id
    )

    active_events = get_all_active_events(
        shipment_id
    )

    now = datetime.utcnow()

    decision = calculate_cumulative_risk(
        completed_events=completed_events,
        active_events=active_events,
        now=now
    )

    risk_breakdown = calculate_risk_breakdown(
        completed_events=completed_events,
        active_events=active_events,
        now=now
    )

    return {
    "shipment_id": shipment_id,
    "integrity_score": decision["integrity_score"],
    "risk_score": decision["risk_score"],
    "status": decision["status"],
    "shock_frequency": decision["shock_frequency"],
    "risk_breakdown": risk_breakdown,
    "latest_telemetry": latest,
    "total_completed_events": len(completed_events),
    "active_events": active_events,
    "event_history": completed_events
    }
