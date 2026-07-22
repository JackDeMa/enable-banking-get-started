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
        self.method = None
        self.url = None
        self.request_body = None
        self.timeout = None

    def request(
        self,
        *,
        method,
        url,
        headers,
        timeout,
        **kwargs,
    ):
        self.method = method
        self.url = url
        self.request_body = kwargs.get("json")
        self.timeout = timeout
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
        request_timeout_seconds=30.0,
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
    assert http_session.method == "POST"
    assert http_session.url == "https://api.example/auth"
    assert http_session.timeout == 30.0

    assert http_session.request_body["state"] == "generated-state"

    assert (
        consume_authorization_flow(
            "generated-state",
            database,
        )
        == "Example Bank_IT"
    )


def test_get_balance_uses_shared_request():
    http_session = FakeHttpSession()

    client = object.__new__(EnableBankingClient)
    client.settings = SimpleNamespace(
        base_url="https://api.example",
        request_timeout_seconds=15.0,
    )
    client.headers = {}
    client._http_session = http_session
    client.sessions = {
        "Example Bank_IT": {
            "session": {
                "accounts_data": [
                    {"uid": "account-123"},
                ],
            },
            "bank": {
                "name": "Example Bank",
                "country": "IT",
            },
        }
    }

    client.get_balance("Example Bank_IT")

    assert http_session.method == "GET"
    assert http_session.url == "https://api.example/accounts/account-123/balances"
    assert http_session.timeout == 15.0
