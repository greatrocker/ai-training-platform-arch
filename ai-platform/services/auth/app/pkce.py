import base64
import hashlib
import secrets

from itsdangerous import BadSignature, URLSafeTimedSerializer

from .config import settings

_serializer = URLSafeTimedSerializer(settings.cookie_signing_secret, salt="oauth-pkce")

PKCE_COOKIE_NAME = "oauth_pkce"
PKCE_MAX_AGE_SEC = 600


def new_pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(40)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def new_state() -> str:
    return secrets.token_urlsafe(24)


def sign_pkce_cookie(state: str, verifier: str) -> str:
    return _serializer.dumps({"state": state, "verifier": verifier})


def read_pkce_cookie(cookie_value: str) -> dict | None:
    try:
        return _serializer.loads(cookie_value, max_age=PKCE_MAX_AGE_SEC)
    except BadSignature:
        return None
