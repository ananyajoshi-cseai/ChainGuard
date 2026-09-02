from datetime import datetime

from database import (
    get_active_event,
    start_active_event,
    update_active_event,
    close_active_event,
    get_shipment_state,
    update_shipment_state,
)

from decision_engine import (
    temperature_severity,
    humidity_severity,
    shock_severity,
    tamper_severity,
)

SHOCK_COOLDOWN_SECONDS = 5


def current_timestamp():
    return datetime.utcnow()


def detect_events(
    shipment_id: str,
    temperature: float,
    humidity: float,
    acceleration: float,
    tamper_status: int,
    timestamp=None
):
    if timestamp is None:
        timestamp = current_timestamp()

    detected_events = []

    # ---------------------------------------------------------
    # TEMPERATURE
    # ---------------------------------------------------------

    temp_severity = temperature_severity(temperature)
    temperature_event = get_active_event(
        shipment_id,
        "temperature"
    )

    if temp_severity > 0:

        if temperature_event is None:

            start_active_event(
                shipment_id,
                "temperature",
                temp_severity,
                timestamp.isoformat()
            )

            detected_events.append({
                "event_type": "temperature",
                "severity": temp_severity,
                "event_status": "started"
            })

        else:

            update_active_event(
                shipment_id,
                "temperature",
                temp_severity,
                timestamp.isoformat()
            )

    elif temperature_event is not None:

        closed = close_active_event(
            shipment_id,
            "temperature"
        )

        detected_events.append({
            "event_type": "temperature",
            "severity": closed["severity"],
            "event_status": "ended",
            "started_at": closed["started_at"],
            "ended_at": closed["last_seen_at"]
        })

    # ---------------------------------------------------------
    # HUMIDITY
    # ---------------------------------------------------------

    humidity_severity_value = humidity_severity(humidity)

    humidity_event = get_active_event(
        shipment_id,
        "humidity"
    )

    if humidity_severity_value > 0:

        if humidity_event is None:

            start_active_event(
                shipment_id,
                "humidity",
                humidity_severity_value,
                timestamp.isoformat()
            )

            detected_events.append({
                "event_type": "humidity",
                "severity": humidity_severity_value,
                "event_status": "started"
            })

        else:

            update_active_event(
                shipment_id,
                "humidity",
                humidity_severity_value,
                timestamp.isoformat()
            )

    elif humidity_event is not None:

        closed = close_active_event(
            shipment_id,
            "humidity"
        )

        detected_events.append({
            "event_type": "humidity",
            "severity": closed["severity"],
            "event_status": "ended",
            "started_at": closed["started_at"],
            "ended_at": closed["last_seen_at"]
        })

    # ---------------------------------------------------------
    # SHOCK
    # ---------------------------------------------------------

    shock_severity_value = shock_severity(
        acceleration
    )

    if shock_severity_value > 0:

        state = get_shipment_state(
            shipment_id
        )

        last_shock_at = (
            None
            if state is None
            else state["last_shock_at"]
        )

        can_record_shock = True

        if last_shock_at:

            previous_time = datetime.fromisoformat(
                last_shock_at
            )

            elapsed = (
                timestamp - previous_time
            ).total_seconds()

            if elapsed < SHOCK_COOLDOWN_SECONDS:
                can_record_shock = False

        if can_record_shock:

            detected_events.append({
                "event_type": "shock",
                "severity": shock_severity_value,
                "event_status": "detected"
            })

            update_shipment_state(
                shipment_id,
                last_shock_at=timestamp.isoformat()
            )

    # ---------------------------------------------------------
    # TAMPER
    # ---------------------------------------------------------

    tamper_severity_value = tamper_severity(
        tamper_status
    )

    tamper_event = get_active_event(
        shipment_id,
        "tamper"
    )

    if tamper_severity_value > 0:

        if tamper_event is None:

            start_active_event(
                shipment_id,
                "tamper",
                tamper_severity_value,
                timestamp.isoformat()
            )

            detected_events.append({
                "event_type": "tamper",
                "severity": tamper_severity_value,
                "event_status": "started"
            })

        else:

            update_active_event(
                shipment_id,
                "tamper",
                tamper_severity_value,
                timestamp.isoformat()
            )

    elif tamper_event is not None:

        closed = close_active_event(
            shipment_id,
            "tamper"
        )

        detected_events.append({
            "event_type": "tamper",
            "severity": closed["severity"],
            "event_status": "ended",
            "started_at": closed["started_at"],
            "ended_at": closed["last_seen_at"]
        })

    # ---------------------------------------------------------
    # SHIPMENT STATE
    # ---------------------------------------------------------

    update_shipment_state(
        shipment_id,
        last_tamper_status=tamper_status
    )

    return detected_events