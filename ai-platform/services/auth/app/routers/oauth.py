from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse

from ..config import settings
from ..pkce import (
    PKCE_COOKIE_NAME,
    PKCE_MAX_AGE_SEC,
    new_pkce_pair,
    new_state,
    read_pkce_cookie,
    sign_pkce_cookie,
)
from ..security import TokenInvalid, extract_identity, verify_access_token

router = APIRouter(tags=["oauth"])

SESSION_AT_COOKIE = "session_at"
SESSION_RT_COOKIE = "session_rt"


def _token_endpoint() -> str:
    return f"{settings.oauth2_issuer}/protocol/openid-connect/token"


def _authorize_endpoint() -> str:
    return f"{settings.oauth2_issuer_public}/protocol/openid-connect/auth"


def _set_session_cookies(response, access_token: str, refresh_token: str | None):
    response.set_cookie(
        SESSION_AT_COOKIE,
        access_token,
        max_age=settings.access_token_ttl_min * 60,
        httponly=True,
        samesite="lax",
    )
    if refresh_token:
        response.set_cookie(
            SESSION_RT_COOKIE,
            refresh_token,
            max_age=settings.refresh_token_ttl_min * 60,
            httponly=True,
            samesite="lax",
        )


@router.get("/login")
async def login():
    verifier, challenge = new_pkce_pair()
    state = new_state()

    params = {
        "client_id": settings.oauth2_client_id,
        "response_type": "code",
        "scope": "openid profile email",
        "redirect_uri": settings.oauth2_redirect_uri,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    redirect = RedirectResponse(url=f"{_authorize_endpoint()}?{urlencode(params)}")
    redirect.set_cookie(
        PKCE_COOKIE_NAME,
        sign_pkce_cookie(state, verifier),
        max_age=PKCE_MAX_AGE_SEC,
        httponly=True,
        samesite="lax",
    )
    return redirect


@router.get("/callback")
async def callback(request: Request, code: str, state: str):
    raw_cookie = request.cookies.get(PKCE_COOKIE_NAME)
    pkce_data = read_pkce_cookie(raw_cookie) if raw_cookie else None
    if not pkce_data or pkce_data.get("state") != state:
        raise HTTPException(status_code=400, detail="invalid or expired oauth state")

    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post(
            _token_endpoint(),
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.oauth2_redirect_uri,
                "client_id": settings.oauth2_client_id,
                "client_secret": settings.oauth2_client_secret,
                "code_verifier": pkce_data["verifier"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if token_resp.status_code != 200:
        raise HTTPException(status_code=401, detail="token exchange failed")

    tokens = token_resp.json()
    redirect = RedirectResponse(url=settings.frontend_origin)
    _set_session_cookies(redirect, tokens["access_token"], tokens.get("refresh_token"))
    redirect.delete_cookie(PKCE_COOKIE_NAME)
    return redirect


@router.post("/refresh")
async def refresh(session_rt: str | None = Cookie(default=None, alias=SESSION_RT_COOKIE)):
    if not session_rt:
        raise HTTPException(status_code=401, detail="no refresh token")

    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post(
            _token_endpoint(),
            data={
                "grant_type": "refresh_token",
                "refresh_token": session_rt,
                "client_id": settings.oauth2_client_id,
                "client_secret": settings.oauth2_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if token_resp.status_code != 200:
        raise HTTPException(status_code=401, detail="refresh failed, please login again")

    tokens = token_resp.json()
    response = JSONResponse({"status": "ok"})
    _set_session_cookies(response, tokens["access_token"], tokens.get("refresh_token"))
    return response


@router.post("/logout")
async def logout():
    response = JSONResponse({"status": "ok"})
    response.delete_cookie(SESSION_AT_COOKIE)
    response.delete_cookie(SESSION_RT_COOKIE)
    return response


@router.get("/me")
async def me(session_at: str | None = Cookie(default=None, alias=SESSION_AT_COOKIE)):
    if not session_at:
        raise HTTPException(status_code=401, detail="not authenticated")
    try:
        claims = await verify_access_token(session_at)
    except TokenInvalid as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return extract_identity(claims)
