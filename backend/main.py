from fastapi import FastAPI
from pydantic import BaseModel

from database import (
    init_db,
    insert_telemetry,
    get_latest_telemetry
)

app = FastAPI(title="ChainGuard API")


class SensorPayload(BaseModel):
    shipment_id: str
    temperature: float
    humidity: float
    acceleration: float
    tamper_status: int


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "ChainGuard API"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/api/telemetry")
def receive_telemetry(data: SensorPayload):

    insert_telemetry(
        data.shipment_id,
        data.temperature,
        data.humidity,
        data.acceleration,
        data.tamper_status
    )

    return {
        "status": "received",
        "shipment_id": data.shipment_id,
        "message": "Telemetry stored successfully"
    }


@app.get("/api/telemetry/latest/{shipment_id}")
def latest_telemetry(shipment_id: str):

    telemetry = get_latest_telemetry(shipment_id)

    if telemetry is None:
        return {
            "status": "not_found",
            "shipment_id": shipment_id
        }

    return telemetry