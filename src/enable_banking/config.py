from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import find_dotenv, load_dotenv


@dataclass(frozen=True)
class Settings:
    pem_file: Path
    base_url: str = "https://api.enablebanking.com"
    redirect_url: str = "https://localhost:8000/callback" # application's redirect URL
    session_memory_json: str = "enable_banking_session.json"

    @property
    def application_id(self) -> str:
        return self.pem_file.stem

    @classmethod
    def from_env(cls) -> "Settings":
        env_file = find_dotenv(usecwd=True)
        load_dotenv(env_file)

        pem_value = os.getenv("PEM_FILE")
        if not pem_value:
            raise RuntimeError("La variabile PEM_FILE non è configurata")
        
        pem_file = Path(pem_value).expanduser()
        if not pem_file.is_absolute():
            base_dir = Path(env_file).parent if env_file else Path.cwd()
            pem_file = base_dir / pem_file

        pem_file = pem_file.resolve()

        if not pem_file.is_file():
            raise FileNotFoundError(
                f"File PEM non trovato: {pem_file}"
            )
        
        return cls(pem_file=pem_file)
