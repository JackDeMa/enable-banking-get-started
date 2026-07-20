from pathlib import Path
import time
import jwt

def create_jwt(
        *, # serve a dire che tutti gli argomenti devono essere passati come keyword arguments
        pem_path: Path,
        application_id: str,
        ttl_seconds: int = 3600,
        now: int | None= None,
) -> str:
    private_key = pem_path.read_text(encoding="utf-8")

    issued_at = int(time.time()) if now is None else now

    payload = {
        "iss": "enablebanking.com",
        "aud": "api.enablebanking.com",
        "iat": issued_at,
        "exp": issued_at + ttl_seconds,
    }

    headers = {
        "typ": "JWT",
        "kid": application_id,
    }

    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers=headers,
    )