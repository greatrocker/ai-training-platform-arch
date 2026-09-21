from fastapi import Header, HTTPException


def current_roles(x_user_roles: str = Header(default="")) -> list[str]:
    return [r for r in x_user_roles.split(",") if r]


def require_role(required: str):
    def _dep(roles: list[str] = Header(default=None, alias="X-User-Roles")) -> None:
        role_list = [r for r in (roles or "").split(",") if r]
        if required not in role_list:
            raise HTTPException(status_code=403, detail=f"requires role '{required}'")

    return _dep
