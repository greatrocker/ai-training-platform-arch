from fastapi import FastAPI

from .routers import datasets

app = FastAPI(title="dataset-service")

app.include_router(datasets.router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
