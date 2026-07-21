from typing import Any, TypedDict
from datetime import datetime, timezone, timedelta

from pprint import pprint

import secrets

import requests
from .auth import create_jwt
from .config import Settings
from .banks import get_bank_key
from .storage import load_latest_session, save_authorization_flow

class BankSessionEntry(TypedDict):
    sessions: dict[str, Any]
    bank: dict[str, Any]


class EnableBankingClient:

    def __init__(self, settings: Settings):
        self.settings = settings
        
        # Client HTTP interno
        self._http_session = requests.Session()

        # Sessioni Enable Banking, indicizzate per banca
        self.sessions: dict[str, BankSessionEntry] = {}

        self.update_headers()

    def _headers(self) -> dict[str, str]:
        token = create_jwt(
            pem_path=self.settings.pem_file,
            application_id=self.settings.application_id,
            )
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            }
    
    def update_headers(self):
        self.headers = self._headers()

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> requests.Response:
        response = self._http_session.request(
            method=method,
            url=f"{self.settings.base_url}{path}",
            headers=self.headers,
            timeout=self.settings.request_timeout_seconds,
            **kwargs,
        )
        response.raise_for_status()
        return response

    def _body_for_new_session(
        self,
        bank,
        state: str,
        psu_type: str = "personal",
    ):
        return {
            "access": {
                "valid_until": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat() # 10 days ahead
                },
            "aspsp": {
                "name": bank["name"], # BANK_NAME
                "country": bank['country'] # BANK_COUNTRY
                },
            "state": state,
            "redirect_url": self.settings.redirect_url, # application's redirect URL
            "psu_type": psu_type,
            }
    
    def get_all_banks(
            self,
            *,
            country: str = "IT",
            psu_type: str = "personal",
            service: str = "AIS",
    ) -> list[dict[str, Any]]:
        response = self._http_session.get(
            f"{self.settings.base_url}/aspsps",
            headers=self.headers,
            params={
                "country": country,
                "psu_type": psu_type,
                "service": service,
            },
        )
        response.raise_for_status()
        return response.json()["aspsps"]
    
    def ask_for_new_session(self, bank):
        """
        Start negotiating a new session and return the authorization response.
        """
        bank_key = get_bank_key(bank)
        state = secrets.token_urlsafe(32)

        save_authorization_flow(
            state=state,
            bank_key=bank_key,
            path=self.settings.session_database,
        )

        response = self._request(
            "POST",
            "/auth",
            json=self._body_for_new_session(
                bank,
                state=state,
            ),
        )

        auth_url = response.json()["url"]
        print(f"To authenticate open URL {auth_url}")
        print("Status:", response.status_code)

        return response
    
    def open_session(self, bank, force_new: bool = False) -> bool:
        """
        Open a session for the given bank. If possible, reuse saved sessions
        """
        bank_key = get_bank_key(bank)
        saved_session = load_latest_session(
            bank_key,
            self.settings.session_database,
        )

        if force_new or saved_session is None:
            print(
                f"Session not available for {bank_key} in "
                f"{self.settings.session_database}, creating a new one"
            )
            r = self.ask_for_new_session(bank)
            return False

        session_id = saved_session["session_id"]
        r = self._http_session.get(f"{self.settings.base_url}/sessions/{session_id}", headers=self.headers)
        r.raise_for_status()

        enable_banking_session  = r.json()
        print("Session ID retrieved from database")

        if enable_banking_session.get("status") == "EXPIRED":
            print("Session expired, creating a new one")
            r = self.ask_for_new_session(bank)
            return False
        
        self.sessions[bank_key] = {
            "session": enable_banking_session,
            "bank": bank,
            }
        return True

    def get_current_session(self, bank_key: str):
        return self.sessions[bank_key]["session"]
    
    def get_balance(self, bank_key: str):
        account_uid = self.sessions[bank_key]["session"]["accounts_data"][0]["uid"]
#        account_uid = self.get_account_uid(bank_key)
        r = self._http_session.get(f"https://api.enablebanking.com/accounts/{account_uid}/balances",headers=self.headers)
        return r.json()
    
    def get_info(self, bank_key: str, info: str = "balances"):
        """
        Questa funzione si può usare per chiamare:
        - "balances",
        - "transactions",
        - "details",
        - "transactions"/{transaction_id}
        """

        account_uid = self.get_account_uid(bank_key)
        r = self._http_session.get(f"https://api.enablebanking.com/accounts/{account_uid}/{info}",headers=self.headers)
        return r.json()
    
    def get_account_uid(self, bank_key: str):
        return self.sessions[bank_key]["session"]["accounts_data"][0]["uid"]
        return __get_account_uid__(self.get_current_session(bank_key))
    
    def disp_balances(self, bank_key, response):
        if "code" in response.keys() and response["code"] == 429:
            print("Rate limit exceeded")
        else:
            balance = response["balances"][0]["balance_amount"]
            print(f"Balance on {bank_key}: {balance['amount']} {balance['currency']}")

    def disp_transactions(self, bank_key, response):
        if "code" in response.keys() and response["code"] == 429:
            print("Rate limit exceeded")
        else:
            print(f"Transactions on {bank_key}:")
            pprint(response["transactions"])

    def authorize_session(self, code: str) -> dict[str, Any]:
        response = self._http_session.post(
            f"{self.settings.base_url}/sessions",
            json={"code": code},
            headers=self.headers,
        )

        response.raise_for_status()
        return response.json()

                
def __get_account_uid__(session):
    if ("accounts_data" in session.keys()) and ("uid" in session["accounts_data"][0].keys()):
        return session["accounts_data"][0]["uid"]
    elif ("accounts" in session.keys()) and ("uid" in session["accounts"][0].keys()):
        return session["accounts"][0]["uid"]
    else:
        print("No valid fields")
        return {}
        

