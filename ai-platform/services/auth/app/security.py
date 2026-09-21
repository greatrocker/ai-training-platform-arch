import time

import httpx
from jose import jwt

from .config import settings

_jwks_cache: dict = {"keys": None, "fetched_at": 0}
_JWKS_TTL_SEC = 300


def _jwks_url() -> str:
    return f"{settings.oauth2_issuer}/protocol/openid-connect/certs"


async def _get_jwks() -> dict:
    now = time.time()
    if _jwks_cache["keys"] is None or now - _jwks_cache["fetched_at"] > _JWKS_TTL_SEC:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(_jwks_url())
            resp.raise_for_status()
            _jwks_cache["keys"] = resp.json()
            _jwks_cache["fetched_at"] = now
    return _jwks_cache["keys"]


class TokenInvalid(Exception):
    pass


async def verify_access_token(token: str) -> dict:
    jwks = await _get_jwks()
    try:
        header = jwt.get_unverified_header(token)
    except Exception as exc:
        raise TokenInvalid(str(exc)) from exc

    key = next((k for k in jwks.get("keys", []) if k.get("kid") == header.get("kid")), None)
    if key is None:
        raise TokenInvalid("signing key not found in JWKS")

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[settings.jwt_algo],
            audience=settings.oauth2_client_id,
            options={"verify_aud": False},
        )
    except Exception as exc:
        raise TokenInvalid(str(exc)) from exc
    return claims


def extract_identity(claims: dict) -> dict:
    realm_roles = (claims.get("realm_access") or {}).get("roles", [])
    return {
        "user_id": claims.get("sub", ""),
        "display_name": claims.get("preferred_username") or claims.get("name") or "",
        "roles": realm_roles,
        "dept": claims.get("dept", ""),
        "groups": claims.get("groups", []),
    }
