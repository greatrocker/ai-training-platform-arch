from fastapi import FastAPI

from .routers import annotations, demos, export, labels, suggest

app = FastAPI(title="annotation-service")

app.include_router(labels.router)
app.include_router(annotations.router)
app.include_router(demos.router)
app.include_router(suggest.router)
app.include_router(export.router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
