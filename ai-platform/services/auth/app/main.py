from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import oauth, verify

app = FastAPI(title="auth-service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(oauth.router, prefix="/api/auth")
app.include_router(verify.router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
