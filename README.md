# ChainGuard

### The Digital Black Box for Sensitive Shipments

ChainGuard is an IoT-powered shipment monitoring system designed to track the condition of sensitive packages during transit.

It collects environmental and physical data such as:

- Temperature
- Humidity
- Motion / acceleration
- Tampering / package opening

The collected telemetry is sent from an ESP32 to a FastAPI backend, where it can be processed to determine the shipment's condition and risk status.
