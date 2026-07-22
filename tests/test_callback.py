from types import SimpleNamespace

from django.test import RequestFactory

from enable_banking.storage import (
    consume_authorization_flow,
    load_latest_session,
    save_authorization_flow,
)
from web.callbacks import views


class FakeClient:
    def __init__(self, settings):
        self.settings = settings

    def authorize_session(self, code):
        assert code == "callback-code"

        return {
            "session_id": "session-from-callback",
            "status": "AUTHORIZED",
            "aspsp": {
                "name": "Example Bank",
                "country": "IT",
            },
            "accounts_data": [],
        }


def test_callback_consumes_state_and_saves_session(
    tmp_path,
    monkeypatch,
):
    database = tmp_path / "sessions.sqlite3"
    settings = SimpleNamespace(
        session_database=database,
    )

    monkeypatch.setattr(
        views.Settings,
        "from_env",
        lambda: settings,
    )
    monkeypatch.setattr(
        views,
        "EnableBankingClient",
        FakeClient,
    )

    save_authorization_flow(
        state="valid-state",
        bank_key="Example Bank_IT",
        path=database,
    )

    request = RequestFactory().get(
        "/callback",
        {
            "code": "callback-code",
            "state": "valid-state",
        },
    )

    response = views.enable_banking_callback(request)

    assert response.status_code == 302
    assert response["Location"] == "/connection/success"

    session = load_latest_session(
        "Example Bank_IT",
        database,
    )
    assert session is not None
    assert session["session_id"] == "session-from-callback"

    assert (
        consume_authorization_flow(
            "valid-state",
            database,
        )
        is None
    )

    replay_response = views.enable_banking_callback(request)
    assert replay_response.status_code == 400
