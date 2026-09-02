# ======================================================
# ChainGuard Decision Engine
# ======================================================
#
# Prototype mathematical model.
#
# The thresholds and weights are configurable demo values
# and must be calibrated for the actual shipment profile
# and physical sensor setup.
#
# ======================================================


# ------------------------------------------------------
# Temperature thresholds
# ------------------------------------------------------

TEMP_MIN = 2.0
TEMP_MAX = 8.0


# ------------------------------------------------------
# Humidity thresholds
# ------------------------------------------------------

HUMIDITY_MIN = 30.0
HUMIDITY_MAX = 70.0


# ------------------------------------------------------
# Event weights
# ------------------------------------------------------

WEIGHTS = {
    "temperature": 8,
    "humidity": 3,
    "shock": 7,
    "tamper": 15
}


# ------------------------------------------------------
# Shock cooldown
# ------------------------------------------------------

SHOCK_COOLDOWN_SECONDS = 5


# ======================================================
# SEVERITY FUNCTIONS
# ======================================================

def temperature_severity(temperature: float) -> int:

    if 2 <= temperature <= 8:
        return 0

    if 0 <= temperature < 2 or 8 < temperature <= 10:
        return 1

    if -2 <= temperature < 0 or 10 < temperature <= 15:
        return 2

    return 3


def humidity_severity(humidity: float) -> int:

    if 30 <= humidity <= 70:
        return 0

    if 20 <= humidity < 30 or 70 < humidity <= 80:
        return 1

    if 10 <= humidity < 20 or 80 < humidity <= 90:
        return 2

    return 3


def shock_severity(acceleration: float) -> int:
    """
    Simulator-calibrated thresholds.

    These values MUST be recalibrated for the
    physical MPU6050 setup.
    """

    if acceleration <= 2.5:
        return 0

    if acceleration <= 4.0:
        return 1

    if acceleration <= 6.0:
        return 2

    return 3


def tamper_severity(tamper_status: int) -> int:

    if tamper_status == 1:
        return 3

    return 0


# ======================================================
# DURATION MULTIPLIER
# ======================================================

def duration_multiplier(duration_seconds: float) -> float:

    duration_minutes = duration_seconds / 60

    if duration_minutes < 1:
        return 1.0

    if duration_minutes <= 5:
        return 1.25

    if duration_minutes <= 15:
        return 1.5

    if duration_minutes <= 30:
        return 2.0

    return 2.5


# ======================================================
# SHOCK FREQUENCY MULTIPLIER
# ======================================================

def shock_frequency_multiplier(frequency: int) -> float:

    if frequency <= 1:
        return 1.0

    if frequency <= 3:
        return 1.25

    if frequency <= 6:
        return 1.5

    return 2.0


# ======================================================
# EVENT RISK
# ======================================================

def calculate_event_risk(
    event_type: str,
    severity: int,
    duration_seconds: float = 0,
    frequency: int = 1
) -> float:

    base_risk = (
        WEIGHTS[event_type] * severity
    )

    if event_type in {
        "temperature",
        "humidity",
        "tamper"
    }:

        multiplier = duration_multiplier(
            duration_seconds
        )

        return base_risk * multiplier

    if event_type == "shock":

        multiplier = shock_frequency_multiplier(
            frequency
        )

        return base_risk * multiplier

    return base_risk


# ======================================================
# SNAPSHOT RISK
# ======================================================

def calculate_snapshot_risk(
    temperature: float,
    humidity: float,
    acceleration: float,
    tamper_status: int
):

    temp_severity = temperature_severity(
        temperature
    )

    humidity_sev = humidity_severity(
        humidity
    )

    shock_sev = shock_severity(
        acceleration
    )

    tamper_sev = tamper_severity(
        tamper_status
    )

    temperature_risk = (
        WEIGHTS["temperature"] * temp_severity
    )

    humidity_risk = (
        WEIGHTS["humidity"] * humidity_sev
    )

    shock_risk = (
        WEIGHTS["shock"] * shock_sev
    )

    tamper_risk = (
        WEIGHTS["tamper"] * tamper_sev
    )

    total_risk = (
        temperature_risk
        + humidity_risk
        + shock_risk
        + tamper_risk
    )

    total_risk = min(
        total_risk,
        100
    )

    integrity_score = 100 - total_risk

    status = get_status(
        integrity_score
    )

    return {
        "integrity_score": integrity_score,
        "risk_score": total_risk,
        "status": status,

        "events": {

            "temperature": {
                "severity": temp_severity,
                "risk": temperature_risk
            },

            "humidity": {
                "severity": humidity_sev,
                "risk": humidity_risk
            },

            "shock": {
                "severity": shock_sev,
                "risk": shock_risk
            },

            "tamper": {
                "severity": tamper_sev,
                "risk": tamper_risk
            }
        }
    }


# ======================================================
# STATUS
# ======================================================

def get_status(integrity_score: float) -> str:

    if integrity_score >= 80:
        return "ACCEPT"

    if integrity_score >= 50:
        return "INSPECT"

    return "HIGH RISK"


# ======================================================
# CUMULATIVE SHIPMENT RISK
# ======================================================

def calculate_cumulative_risk(
    completed_events,
    active_events,
    now
):
    """
    Calculates risk from the shipment's event history.

    Completed events contribute their stored risk.

    Active environmental/tamper events contribute their
    current risk based on elapsed duration.

    Shock frequency is handled across the shipment's
    completed shock events.
    """

    total_risk = 0

    shock_count = 0

    # --------------------------------------------------
    # Completed events
    # --------------------------------------------------

    for event in completed_events:

        event_type = event["event_type"]

        severity = event["severity"]

        duration = event["duration_seconds"]

        if event_type == "shock":
            shock_count += 1
            continue

        risk = calculate_event_risk(
            event_type=event_type,
            severity=severity,
            duration_seconds=duration,
            frequency=event["frequency"]
        )

        total_risk += risk

    # --------------------------------------------------
    # Shock frequency
    # --------------------------------------------------

    for event in completed_events:

        if event["event_type"] == "shock":

            risk = calculate_event_risk(
                event_type="shock",
                severity=event["severity"],
                frequency=shock_count
            )

            total_risk += risk

    # --------------------------------------------------
    # Active events
    # --------------------------------------------------

    for event in active_events:

        event_type = event["event_type"]

        severity = event["severity"]

        started_at = event["started_at"]

        started_time = parse_timestamp(
            started_at
        )

        duration_seconds = (
            now - started_time
        ).total_seconds()

        risk = calculate_event_risk(
            event_type=event_type,
            severity=severity,
            duration_seconds=max(
                duration_seconds,
                0
            )
        )

        total_risk += risk

    # --------------------------------------------------
    # Cap risk
    # --------------------------------------------------

    total_risk = min(
        round(total_risk, 2),
        100
    )

    integrity_score = round(
        100 - total_risk,
        2
    )

    status = get_status(
        integrity_score
    )

    return {
        "integrity_score": integrity_score,
        "risk_score": total_risk,
        "status": status,
        "shock_frequency": shock_count
    }


# ======================================================
# TIMESTAMP HELPER
# ======================================================

def parse_timestamp(timestamp: str):

    return __import__(
        "datetime"
    ).datetime.fromisoformat(
        timestamp
    )


# ======================================================
# TEST
# ======================================================

if __name__ == "__main__":

    result = calculate_snapshot_risk(
        temperature=5.0,
        humidity=60.0,
        acceleration=7.0,
        tamper_status=0
    )

    print(result)