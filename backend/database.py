import sqlite3

DB_NAME = "chainguard.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()

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

    conn.commit()
    conn.close()


def insert_telemetry(
    shipment_id,
    temperature,
    humidity,
    acceleration,
    tamper_status
):
    conn = get_connection()

    conn.execute("""
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
    conn.close()


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