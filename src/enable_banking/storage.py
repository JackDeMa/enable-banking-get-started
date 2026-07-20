import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

def save_session(
    session: Mapping[str, Any],
    path: str | Path,
) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    destination.write_text(
        json.dumps(session, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

def save_session_id(
    session: Mapping[str, Any],
    path: str | Path,
) -> None:
    session_id = session.get("session_id")
    aspsp = session.get("aspsp")
    if not isinstance(session_id, str) or not session_id:
        raise ValueError(
            "La sessione non contiene un session_id valido"
        )
    if not isinstance(aspsp, Mapping):
        raise ValueError(
            "La sessione non contiene dati ASPSP validi"
        )
    name = aspsp.get("name")
    country = aspsp.get("country")
    if not isinstance(name, str) or not isinstance(country, str):
        raise ValueError(
            "I dati ASPSP non contengono name e country"
        )
    bank_key = f"{name}_{country}"
    destination = Path(path)
    saved_sessions = load_session(destination) or {}
    saved_sessions[bank_key] = session_id
    save_session(saved_sessions, destination)

def load_session(path: str | Path) -> dict[str, Any] | None:
    source = Path(path)

    if not source.exists():
        return None

    data = json.loads(
        source.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise ValueError(
            f"Il file non contiene un oggetto JSON: {path}"
        )

    return data
