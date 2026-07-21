import json
import sqlite3
from collections.abc import Mapping
from contextlib import closing
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS enable_banking_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,
    bank_key TEXT NOT NULL,
    bank_name TEXT NOT NULL,
    bank_country TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_enable_banking_sessions_bank_key
    ON enable_banking_sessions (bank_key, id DESC);

CREATE TABLE IF NOT EXISTS authorization_flows (
    state TEXT PRIMARY KEY,
    bank_key TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    consumed_at TEXT
);
"""

def _connect(path: str | Path) -> sqlite3.Connection:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(destination, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript(SCHEMA)
    except Exception:
        connection.close()
        raise
    return connection


def _session_fields(session: Mapping[str, Any]) -> tuple[str, str, str, str]:
    session_id = session.get("session_id")
    aspsp = session.get("aspsp")

    if not isinstance(session_id, str) or not session_id:
        raise ValueError("La sessione non contiene un session_id valido")
    if not isinstance(aspsp, Mapping):
        raise ValueError("La sessione non contiene dati ASPSP validi")

    bank_name = aspsp.get("name")
    bank_country = aspsp.get("country")
    if not isinstance(bank_name, str) or not bank_name:
        raise ValueError("I dati ASPSP non contengono un name valido")
    if not isinstance(bank_country, str) or not bank_country:
        raise ValueError("I dati ASPSP non contengono un country valido")

    bank_key = f"{bank_name}_{bank_country}"
    return session_id, bank_key, bank_name, bank_country


def save_session(
    session: Mapping[str, Any],
    path: str | Path,
) -> None:
    """Insert a complete Enable Banking session, updating duplicate session IDs."""
    session_id, bank_key, bank_name, bank_country = _session_fields(session)
    payload_json = json.dumps(session, ensure_ascii=False, separators=(",", ":"))

    with closing(_connect(path)) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO enable_banking_sessions (
                    session_id,
                    bank_key,
                    bank_name,
                    bank_country,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    bank_key = excluded.bank_key,
                    bank_name = excluded.bank_name,
                    bank_country = excluded.bank_country,
                    payload_json = excluded.payload_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (session_id, bank_key, bank_name, bank_country, payload_json),
            )


def load_latest_session(
    bank_key: str,
    path: str | Path,
) -> dict[str, Any] | None:
    """Return the complete payload of the newest stored session for a bank."""
    with closing(_connect(path)) as connection:
        row = connection.execute(
            """
            SELECT payload_json
            FROM enable_banking_sessions
            WHERE bank_key = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (bank_key,),
        ).fetchone()

    if row is None:
        return None

    session = json.loads(row["payload_json"])
    if not isinstance(session, dict):
        raise ValueError("Il record della sessione non contiene un oggetto JSON")
    return session

def save_authorization_flow(
    state: str,
    bank_key: str,
    path: str | Path,
) -> None:
    """Store a pending authorization flow."""
    if not state:
        raise ValueError("Lo state non può essere vuoto")
    if not bank_key:
        raise ValueError("La bank_key non può essere vuota")

    with closing(_connect(path)) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO authorization_flows (
                    state,
                    bank_key
                ) VALUES (?, ?)
                """,
                (state, bank_key),
            )

def consume_authorization_flow(
    state: str,
    path: str | Path,
    *,
    max_age_seconds: int = 600,
) -> str | None:
    """Consume a pending state and return its bank key."""
    if not state:
        return None
    if max_age_seconds <= 0:
        raise ValueError("max_age_seconds deve essere positivo")

    minimum_created_at = f"-{max_age_seconds} seconds"

    with closing(_connect(path)) as connection:
        with connection:
            cursor = connection.execute(
                """
                UPDATE authorization_flows
                SET consumed_at = CURRENT_TIMESTAMP
                WHERE state = ?
                  AND consumed_at IS NULL
                  AND created_at >= datetime('now', ?)
                """,
                (state, minimum_created_at),
            )

            if cursor.rowcount != 1:
                return None

            row = connection.execute(
                """
                SELECT bank_key
                FROM authorization_flows
                WHERE state = ?
                """,
                (state,),
            ).fetchone()

    return row["bank_key"] if row is not None else None