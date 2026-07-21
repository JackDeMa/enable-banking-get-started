from types import SimpleNamespace

from enable_banking import client as client_module
from enable_banking.client import EnableBankingClient
from enable_banking.storage import consume_authorization_flow


class FakeResponse:
    status_code = 200

    def json(self):
        return {"url": "https://bank.example/authorize"}

    def raise_for_status(self):
        pass


class FakeHttpSession:
    def __init__(self):
        self.request_body = None

    def post(self, url, *, json, headers):
        self.request_body = json
        return FakeResponse()


def test_ask_for_new_session_saves_generated_state(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        client_module.secrets,
        "token_urlsafe",
        lambda size: "generated-state",
    )

    database = tmp_path / "sessions.sqlite3"
    http_session = FakeHttpSession()

    client = object.__new__(EnableBankingClient)
    client.settings = SimpleNamespace(
        base_url="https://api.example",
        redirect_url="https://localhost:8000/callback",
        session_database=database,
    )
    client.headers = {}
    client._http_session = http_session

    bank = {
        "name": "Example Bank",
        "country": "IT",
    }

    client.ask_for_new_session(bank)

    assert http_session.request_body["state"] == "generated-state"

    assert (
        consume_authorization_flow(
            "generated-state",
            database,
        )
        == "Example Bank_IT"
    )