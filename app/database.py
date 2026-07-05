from pathlib import Path
import sqlite3


DB_PATH = Path("data") / "mechmate.db"


def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def init_db():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                make TEXT NOT NULL,
                model TEXT NOT NULL,
                mileage INTEGER NOT NULL,
                engine TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS diagnostic_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER,
                input_text TEXT NOT NULL,
                summary TEXT NOT NULL,
                severity TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
            )
            """
        )

        connection.commit()


def add_vehicle(year: int, make: str, model: str, mileage: int, engine: str = ""):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO vehicles (year, make, model, mileage, engine)
            VALUES (?, ?, ?, ?, ?)
            """,
            (year, make, model, mileage, engine),
        )

        connection.commit()
        return cursor.lastrowid


def get_vehicles():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, year, make, model, mileage, engine, created_at
            FROM vehicles
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()

        return [dict(row) for row in rows]


def get_vehicle(vehicle_id: int):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, year, make, model, mileage, engine, created_at
            FROM vehicles
            WHERE id = ?
            """,
            (vehicle_id,),
        ).fetchone()

        if row is None:
            return None

        return dict(row)


def add_diagnostic_session(
    vehicle_id: int | None,
    input_text: str,
    summary: str,
    severity: str,
):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO diagnostic_sessions (
                vehicle_id,
                input_text,
                summary,
                severity
            )
            VALUES (?, ?, ?, ?)
            """,
            (vehicle_id, input_text, summary, severity),
        )

        connection.commit()
        return cursor.lastrowid


def get_diagnostic_history():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                diagnostic_sessions.id,
                diagnostic_sessions.vehicle_id,
                diagnostic_sessions.input_text,
                diagnostic_sessions.summary,
                diagnostic_sessions.severity,
                diagnostic_sessions.created_at,
                vehicles.year,
                vehicles.make,
                vehicles.model,
                vehicles.mileage,
                vehicles.engine
            FROM diagnostic_sessions
            LEFT JOIN vehicles
                ON diagnostic_sessions.vehicle_id = vehicles.id
            ORDER BY diagnostic_sessions.created_at DESC, diagnostic_sessions.id DESC
            """
        ).fetchall()

        return [dict(row) for row in rows]