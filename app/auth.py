import base64
import hashlib
import hmac
import os
import secrets
import time


SESSION_COOKIE_NAME = "mechmate_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7
_SESSION_SECRET = os.environ.get("MECHMATE_SESSION_SECRET") or secrets.token_urlsafe(32)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived_key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
    )
    return f"scrypt$16384$8$1${_encode(salt)}${_encode(derived_key)}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected_key = stored_hash.split("$")
        if algorithm != "scrypt":
            return False

        actual_key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
        )
        return hmac.compare_digest(actual_key, _decode(expected_key))
    except (TypeError, ValueError):
        return False


def create_session_token(user_id: int) -> str:
    expires_at = int(time.time()) + SESSION_MAX_AGE
    payload = f"{user_id}:{expires_at}".encode("utf-8")
    signature = hmac.new(
        _SESSION_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).digest()
    return f"{_encode(payload)}.{_encode(signature)}"


def get_session_user_id(token: str | None) -> int | None:
    if not token or "." not in token:
        return None

    try:
        encoded_payload, encoded_signature = token.split(".", maxsplit=1)
        payload = _decode(encoded_payload)
        expected_signature = hmac.new(
            _SESSION_SECRET.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).digest()

        if not hmac.compare_digest(expected_signature, _decode(encoded_signature)):
            return None

        user_id, expires_at = payload.decode("utf-8").split(":", maxsplit=1)
        if int(expires_at) < int(time.time()):
            return None

        return int(user_id)
    except (TypeError, ValueError):
        return None
