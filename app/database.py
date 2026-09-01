from pathlib import Path
import sqlite3
import json


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
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                make TEXT NOT NULL,
                model TEXT NOT NULL,
                mileage INTEGER NOT NULL,
                engine TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS diagnostic_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                vehicle_id INTEGER,
                input_text TEXT NOT NULL,
                summary TEXT NOT NULL,
                severity TEXT NOT NULL,
                causes TEXT DEFAULT '[]',
                inspection TEXT DEFAULT '[]',
                parts TEXT DEFAULT '[]',
                parts_store_notes TEXT DEFAULT '[]',
                safety TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
            )
            """
        )

        # Migration section:
        # Add ownership columns and full-diagnosis fields to databases created
        # by earlier versions without deleting their existing records. Legacy
        # records remain unassigned until an explicit migration is added.
        vehicle_columns = connection.execute(
            "PRAGMA table_info(vehicles)"
        ).fetchall()
        vehicle_column_names = [column["name"] for column in vehicle_columns]

        if "user_id" not in vehicle_column_names:
            connection.execute("ALTER TABLE vehicles ADD COLUMN user_id INTEGER")

        existing_columns = connection.execute(
            "PRAGMA table_info(diagnostic_sessions)"
        ).fetchall()

        existing_column_names = [column["name"] for column in existing_columns]

        new_columns = {
            "user_id": "INTEGER",
            "causes": "TEXT DEFAULT '[]'",
            "inspection": "TEXT DEFAULT '[]'",
            "parts": "TEXT DEFAULT '[]'",
            "parts_store_notes": "TEXT DEFAULT '[]'",
            "safety": "TEXT DEFAULT ''",
        }

        for column_name, column_definition in new_columns.items():
            if column_name not in existing_column_names:
                connection.execute(
                    f"ALTER TABLE diagnostic_sessions ADD COLUMN {column_name} {column_definition}"
                )

        connection.commit()


def add_user(email: str, password_hash: str):
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (email, password_hash)
                VALUES (?, ?)
                """,
                (email, password_hash),
            )
            connection.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None


def get_user_by_email(email: str):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, email, password_hash, created_at
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

        return dict(row) if row else None


def get_user_by_id(user_id: int):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, email, created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

        return dict(row) if row else None


def add_vehicle(
    user_id: int,
    year: int,
    make: str,
    model: str,
    mileage: int,
    engine: str = "",
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO vehicles (user_id, year, make, model, mileage, engine)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, year, make, model, mileage, engine),
        )

        connection.commit()
        return cursor.lastrowid


def get_vehicles(user_id: int) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, year, make, model, mileage, engine, created_at
            FROM vehicles
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (user_id,),
        ).fetchall()

        return [dict(row) for row in rows]


def get_vehicle(vehicle_id: int, user_id: int) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, year, make, model, mileage, engine, created_at
            FROM vehicles
            WHERE id = ? AND user_id = ?
            """,
            (vehicle_id, user_id),
        ).fetchone()

        if row is None:
            return None

        return dict(row)


def add_diagnostic_session(
    user_id: int,
    vehicle_id: int | None,
    input_text: str,
    summary: str,
    severity: str,
    causes: list[str],
    inspection: list[str],
    parts: list[str],
    parts_store_notes: list[str],
    safety: str,
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO diagnostic_sessions (
                user_id,
                vehicle_id,
                input_text,
                summary,
                severity,
                causes,
                inspection,
                parts,
                parts_store_notes,
                safety
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                vehicle_id,
                input_text,
                summary,
                severity,
                json.dumps(causes),
                json.dumps(inspection),
                json.dumps(parts),
                json.dumps(parts_store_notes),
                safety,
            ),
        )

        connection.commit()
        return cursor.lastrowid


def get_diagnostic_history(user_id: int) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                diagnostic_sessions.id,
                diagnostic_sessions.user_id,
                diagnostic_sessions.vehicle_id,
                diagnostic_sessions.input_text,
                diagnostic_sessions.summary,
                diagnostic_sessions.severity,
                diagnostic_sessions.causes,
                diagnostic_sessions.inspection,
                diagnostic_sessions.parts,
                diagnostic_sessions.parts_store_notes,
                diagnostic_sessions.safety,
                diagnostic_sessions.created_at,
                vehicles.year,
                vehicles.make,
                vehicles.model,
                vehicles.mileage,
                vehicles.engine
            FROM diagnostic_sessions
            LEFT JOIN vehicles
                ON diagnostic_sessions.vehicle_id = vehicles.id
                AND diagnostic_sessions.user_id = vehicles.user_id
            WHERE diagnostic_sessions.user_id = ?
            ORDER BY diagnostic_sessions.created_at DESC, diagnostic_sessions.id DESC
            """,
            (user_id,),
        ).fetchall()

        history = []

        for row in rows:
            item = dict(row)

            item["causes"] = json.loads(item["causes"] or "[]")
            item["inspection"] = json.loads(item["inspection"] or "[]")
            item["parts"] = json.loads(item["parts"] or "[]")
            item["parts_store_notes"] = json.loads(item["parts_store_notes"] or "[]")

            history.append(item)

        return history
