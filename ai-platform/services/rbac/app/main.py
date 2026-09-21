from fastapi import FastAPI

from .routers import departments, groups, permissions, roles, users

app = FastAPI(title="rbac-service")

prefix = "/api/rbac"
app.include_router(departments.router, prefix=prefix)
app.include_router(groups.router, prefix=prefix)
app.include_router(roles.router, prefix=prefix)
app.include_router(permissions.router, prefix=prefix)
app.include_router(users.router, prefix=prefix)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
