"""Minimal signed bearer tokens for anonymous review authorship."""
import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Dict

from fastapi import Header, HTTPException

from config import AUTH_SECRET, AUTH_TOKEN_TTL_SECONDS


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_anonymous_token() -> tuple[str, str]:
    user_id = f"anon_{secrets.token_urlsafe(18)}"
    header = _encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _encode(json.dumps({
        "sub": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + AUTH_TOKEN_TTL_SECONDS,
    }, separators=(",", ":")).encode())
    unsigned = f"{header}.{payload}".encode("ascii")
    signature = _encode(hmac.new(AUTH_SECRET.encode(), unsigned, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}", user_id


def verify_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer 인증이 필요합니다")

    token = authorization[7:].strip()
    try:
        header, payload, signature = token.split(".")
        unsigned = f"{header}.{payload}".encode("ascii")
        expected = _encode(hmac.new(AUTH_SECRET.encode(), unsigned, hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")

        claims: Dict[str, object] = json.loads(_decode(payload))
        subject = claims.get("sub")
        expires_at = int(claims.get("exp", 0))
        if not isinstance(subject, str) or not subject or expires_at <= int(time.time()):
            raise ValueError("invalid claims")
        return subject
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="유효하지 않은 인증 토큰입니다")


def get_current_user(authorization: str | None = Header(None)) -> str:
    return verify_bearer_token(authorization)
