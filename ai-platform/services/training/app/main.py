from fastapi import FastAPI

from .routers import bootstrap, jobs

app = FastAPI(title="training-service")

app.include_router(bootstrap.router)
app.include_router(jobs.router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# bootstrap-label (Page3 semi-automatic annotation) trains a throwaway
# model from the dataset's own current annotations purely to auto-suggest
# labels for the rest of the images — separate from /jobs above, which are
# first-class model_registry/training_job entries (Page4).
