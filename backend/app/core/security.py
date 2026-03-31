import base64
import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Iterable
from typing import Any

from app.core.config import settings

PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 600_000


class TokenValidationError(ValueError):
    pass


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("utf-8")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    )
    return f"{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${salt}${derived_key.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, iterations_raw, salt, stored_hash = password_hash.split("$", 3)
    except ValueError:
        return False

    if scheme != PASSWORD_SCHEME:
        return False

    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations_raw),
    )
    return hmac.compare_digest(derived_key.hex(), stored_hash)


def create_access_token(subject: str, role: str, expires_in: int | None = None) -> str:
    now = int(time.time())
    ttl = expires_in or settings.auth_access_token_expire_seconds
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + ttl,
        "iss": settings.app_name,
    }

    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = hmac.new(
        settings.auth_secret_key.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError as exc:
        raise TokenValidationError("Malformed access token.") from exc

    signing_input = f"{encoded_header}.{encoded_payload}"
    expected_signature = hmac.new(
        settings.auth_secret_key.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(_b64url_encode(expected_signature), encoded_signature):
        raise TokenValidationError("Invalid access token signature.")

    try:
        payload = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise TokenValidationError("Invalid access token payload.") from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise TokenValidationError("Access token has expired.")

    if payload.get("iss") != settings.app_name:
        raise TokenValidationError("Access token issuer mismatch.")

    if not payload.get("sub"):
        raise TokenValidationError("Access token subject is missing.")

    return payload
