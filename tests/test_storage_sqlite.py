import json
import sqlite3

import pytest

from enable_banking.storage import load_latest_session, save_session


def make_session(session_id: str, *, status: str = "AUTHORIZED") -> dict:
    return {
        "session_id": session_id,
        "status": status,
        "aspsp": {"name": "Example Bank", "country": "IT"},
        "accounts_data": [{"uid": f"account-{session_id}"}],
        "extra": {"preserved": True},
    }


def test_save_session_preserves_the_complete_payload(tmp_path):
    database = tmp_path / "sessions.sqlite3"
    session = make_session("session-1")

    save_session(session, database)

    assert load_latest_session("Example Bank_IT", database) == session

    with sqlite3.connect(database) as connection:
        row = connection.execute(
            """
            SELECT session_id, bank_name, bank_country, payload_json
            FROM enable_banking_sessions
            """
        ).fetchone()

    assert row[:3] == ("session-1", "Example Bank", "IT")
    assert json.loads(row[3]) == session


def test_latest_session_is_selected_and_duplicate_ids_are_updated(tmp_path):
    database = tmp_path / "sessions.sqlite3"
    first_session = make_session("session-1")
    latest_session = make_session("session-2")

    save_session(first_session, database)
    save_session(latest_session, database)
    save_session(make_session("session-2", status="EXPIRED"), database)

    stored = load_latest_session("Example Bank_IT", database)
    assert stored is not None
    assert stored["session_id"] == "session-2"
    assert stored["status"] == "EXPIRED"

    with sqlite3.connect(database) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM enable_banking_sessions"
        ).fetchone()[0]

    assert count == 2


def test_save_session_rejects_incomplete_payloads(tmp_path):
    with pytest.raises(ValueError, match="session_id"):
        save_session({"aspsp": {"name": "Example Bank", "country": "IT"}}, tmp_path / "db")
