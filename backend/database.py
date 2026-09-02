import sqlite3


DB_NAME = "chainguard.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()

    # --------------------------------------------------
    # Raw telemetry
    # --------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id TEXT NOT NULL,
            temperature REAL,
            humidity REAL,
            acceleration REAL,
            tamper_status INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --------------------------------------------------
    # Completed / recorded events
    # --------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            severity INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            duration_seconds REAL DEFAULT 0,
            frequency INTEGER DEFAULT 1,
            risk_contribution REAL DEFAULT 0
        )
    """)

    # --------------------------------------------------
    # Currently active events
    #
    # Used for environmental excursions and tampering.
    # --------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS active_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            severity INTEGER NOT NULL,
            started_at DATETIME NOT NULL,
            last_seen_at DATETIME NOT NULL,
            UNIQUE(shipment_id, event_type)
        )
    """)

    # --------------------------------------------------
    # Last known sensor state
    # --------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS shipment_state (
            shipment_id TEXT PRIMARY KEY,
            last_shock_at DATETIME,
            last_tamper_status INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


# ======================================================
# TELEMETRY
# ======================================================

def insert_telemetry(
    shipment_id,
    temperature,
    humidity,
    acceleration,
    tamper_status
):
    conn = get_connection()

    cursor = conn.execute("""
        INSERT INTO telemetry (
            shipment_id,
            temperature,
            humidity,
            acceleration,
            tamper_status
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        shipment_id,
        temperature,
        humidity,
        acceleration,
        tamper_status
    ))

    conn.commit()

    telemetry_id = cursor.lastrowid

    conn.close()

    return telemetry_id


def get_latest_telemetry(shipment_id):
    conn = get_connection()

    row = conn.execute("""
        SELECT *
        FROM telemetry
        WHERE shipment_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (shipment_id,)).fetchone()

    conn.close()

    return dict(row) if row else None


def get_recent_telemetry(shipment_id, limit=50):
    conn = get_connection()

    rows = conn.execute("""
        SELECT *
        FROM telemetry
        WHERE shipment_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (shipment_id, limit)).fetchall()

    conn.close()

    return [dict(row) for row in rows]


# ======================================================
# COMPLETED EVENTS
# ======================================================

def insert_event(
    shipment_id,
    event_type,
    severity,
    duration_seconds=0,
    frequency=1,
    risk_contribution=0
):
    conn = get_connection()

    cursor = conn.execute("""
        INSERT INTO events (
            shipment_id,
            event_type,
            severity,
            duration_seconds,
            frequency,
            risk_contribution
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        shipment_id,
        event_type,
        severity,
        duration_seconds,
        frequency,
        risk_contribution
    ))

    conn.commit()

    event_id = cursor.lastrowid

    conn.close()

    return event_id


def get_recent_events(shipment_id, limit=50):
    conn = get_connection()

    rows = conn.execute("""
        SELECT *
        FROM events
        WHERE shipment_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (shipment_id, limit)).fetchall()

    conn.close()

    return [dict(row) for row in rows]


def get_all_events(shipment_id):
    conn = get_connection()

    rows = conn.execute("""
        SELECT *
        FROM events
        WHERE shipment_id = ?
        ORDER BY id ASC
    """, (shipment_id,)).fetchall()

    conn.close()

    return [dict(row) for row in rows]


# ======================================================
# ACTIVE EVENTS
# ======================================================

def get_active_event(shipment_id, event_type):
    conn = get_connection()

    row = conn.execute("""
        SELECT *
        FROM active_events
        WHERE shipment_id = ?
        AND event_type = ?
        LIMIT 1
    """, (shipment_id, event_type)).fetchone()

    conn.close()

    return dict(row) if row else None


def start_active_event(
    shipment_id,
    event_type,
    severity,
    timestamp
):
    conn = get_connection()

    conn.execute("""
        INSERT INTO active_events (
            shipment_id,
            event_type,
            severity,
            started_at,
            last_seen_at
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(shipment_id, event_type)
        DO UPDATE SET
            severity = MAX(active_events.severity, excluded.severity),
            last_seen_at = excluded.last_seen_at
    """, (
        shipment_id,
        event_type,
        severity,
        timestamp,
        timestamp
    ))

    conn.commit()
    conn.close()


def update_active_event(
    shipment_id,
    event_type,
    severity,
    timestamp
):
    conn = get_connection()

    conn.execute("""
        UPDATE active_events
        SET
            severity = MAX(severity, ?),
            last_seen_at = ?
        WHERE shipment_id = ?
        AND event_type = ?
    """, (
        severity,
        timestamp,
        shipment_id,
        event_type
    ))

    conn.commit()
    conn.close()


def close_active_event(shipment_id, event_type):
    conn = get_connection()

    row = conn.execute("""
        SELECT *
        FROM active_events
        WHERE shipment_id = ?
        AND event_type = ?
        LIMIT 1
    """, (shipment_id, event_type)).fetchone()

    if row is None:
        conn.close()
        return None

    event = dict(row)

    conn.execute("""
        DELETE FROM active_events
        WHERE shipment_id = ?
        AND event_type = ?
    """, (shipment_id, event_type))

    conn.commit()
    conn.close()

    return event


def get_all_active_events(shipment_id):
    conn = get_connection()

    rows = conn.execute("""
        SELECT *
        FROM active_events
        WHERE shipment_id = ?
        ORDER BY id ASC
    """, (shipment_id,)).fetchall()

    conn.close()

    return [dict(row) for row in rows]


# ======================================================
# SHIPMENT STATE
# ======================================================

def get_shipment_state(shipment_id):
    conn = get_connection()

    row = conn.execute("""
        SELECT *
        FROM shipment_state
        WHERE shipment_id = ?
        LIMIT 1
    """, (shipment_id,)).fetchone()

    conn.close()

    return dict(row) if row else None


def update_shipment_state(
    shipment_id,
    last_shock_at=None,
    last_tamper_status=None
):
    conn = get_connection()

    existing = conn.execute("""
        SELECT *
        FROM shipment_state
        WHERE shipment_id = ?
    """, (shipment_id,)).fetchone()

    if existing is None:

        conn.execute("""
            INSERT INTO shipment_state (
                shipment_id,
                last_shock_at,
                last_tamper_status
            )
            VALUES (?, ?, ?)
        """, (
            shipment_id,
            last_shock_at,
            0 if last_tamper_status is None else last_tamper_status
        ))

    else:

        current_shock = existing["last_shock_at"]
        current_tamper = existing["last_tamper_status"]

        conn.execute("""
            UPDATE shipment_state
            SET
                last_shock_at = ?,
                last_tamper_status = ?
            WHERE shipment_id = ?
        """, (
            last_shock_at if last_shock_at is not None else current_shock,
            last_tamper_status if last_tamper_status is not None else current_tamper,
            shipment_id
        ))

    conn.commit()
    conn.close()