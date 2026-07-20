from typing import Any, TypedDict
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json

from pprint import pprint


import requests
from .auth import create_jwt
from .config import Settings
from .banks import get_bank_key
from .storage import load_session, save_session_id

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

    def _body_for_new_session(self, bank, psu_type: str = "personal"):
        return {
            "access": {
                "valid_until": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat() # 10 days ahead
                },
            "aspsp": {
                "name": bank["name"], # BANK_NAME
                "country": bank['country'] # BANK_COUNTRY
                },
            "state": "123e4567-e89b-12d3-a456-426614174000",
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
        If no session is available, start negotiating a new one obtaining the access link
        """
        r = self._http_session.post(f"{self.settings.base_url}/auth", json=self._body_for_new_session(bank), headers=self.headers)
        auth_url = r.json()['url']
        print(f"To authenticate open URL {auth_url}") # open this URL in a web browser
        print("Status:", r.status_code)
        r.raise_for_status()
        return r
    
    # def create_new_session(self, code: str, bank: dict[str, Any]) -> dict[str, Any]:
    #     """
    #     End new session negotiation by passing the session code
    #     """
    #     print("Running create_new_session")
    #     response = self._http_session.post(f"{self.settings.base_url}/sessions", json={"code": code}, headers=self.headers)
    #     response.raise_for_status()
    #     enable_banking_session = response.json()
    #     bank_key = get_bank_key(bank)
    #     self.sessions[bank_key] = {
    #         "session": enable_banking_session,
    #         "bank": bank,
    #     }
    #     save_session_id()
    #     self.save_bank_session_id(session=self.sessions[bank_key]["session"])
    #     self.open_session(bank, force_new=False)

    #     return enable_banking_session
    
    # def save_bank_session_id(self, session):
    #     """
    #     Save session id in the json for future reuse
    #     """
    #     session = load_session(self.session_file_path)
    #     bank = session['aspsp']
    #     sessions[get_bank_key(bank)] = session["session_id"]
    #     self.session_file_path.write_text(json.dumps(sessions, indent=2))
    #     print("Session saved to file")

    # def load_saved_sessions(self):
    #     self.session_file_path = Path(self.settings.session_memory_json)
    #     if not self.session_file_path.is_file():
    #         self.session_file_path = self.session_file_path.resolve()
    #     return json.loads(self.session_file_path.read_text()) if self.session_file_path.exists() else {}
    
    def open_session(self, bank, force_new: bool = False) -> bool:
        """
        Open a session for the given bank. If possible, reuse saved sessions
        """
        bank_key = get_bank_key(bank)
        saved_sessions = load_session(self.settings.session_memory_json)

        if force_new or (saved_sessions is None) or (bank_key not in saved_sessions):
            print("Session not available, creating a new one")
            r = self.ask_for_new_session(bank)
            return False

        session_id = saved_sessions[bank_key]
        r = self._http_session.get(f"{self.settings.base_url}/sessions/{session_id}", headers=self.headers)
        r.raise_for_status()

        enable_banking_session  = r.json()
        print("Session ID retrieved from saving")

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
            print(f"Balance on {bank_key}: {response["balances"][0]["balance_amount"]["amount"]} {response["balances"][0]["balance_amount"]["currency"]}")

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
        

