from fastapi import APIRouter, Cookie, HTTPException, Response

from ..security import TokenInvalid, extract_identity, verify_access_token

router = APIRouter(tags=["verify"])


@router.get("/verify")
async def verify(session_at: str | None = Cookie(default=None, alias="session_at")):
    if not session_at:
        raise HTTPException(status_code=401, detail="no session")
    try:
        claims = await verify_access_token(session_at)
    except TokenInvalid as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    identity = extract_identity(claims)
    response = Response(status_code=200)
    response.headers["X-User-Id"] = identity["user_id"]
    response.headers["X-User-Roles"] = ",".join(identity["roles"])
    response.headers["X-User-Dept"] = identity["dept"] or ""
    response.headers["X-User-Groups"] = ",".join(identity["groups"])
    return response
