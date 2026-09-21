from fastapi import FastAPI

from .routers import devices, flows

app = FastAPI(title="pipeline-service")

app.include_router(flows.router)
app.include_router(devices.router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
