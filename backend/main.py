from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="ChainGuard API")


class SensorPayload(BaseModel):
    shipment_id: str
    temperature: float
    humidity: float
    acceleration: float
    tamper_status: int


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

    print("Received telemetry:")
    print(data.model_dump())

    return {
        "status": "received",
        "shipment_id": data.shipment_id,
        "message": "Telemetry received successfully"
    }