from fastapi import FastAPI

app = FastAPI(title="monitor-service")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# TODO: implement Page6 flow per architecture doc section 3 —
# HLS/WebRTC stream relay, alarm_event CRUD, WebSocket push via Redis pub/sub.
