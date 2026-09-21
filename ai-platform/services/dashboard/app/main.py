from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="dashboard-service")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.websocket("/api/dashboard/ws")
async def dashboard_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass


# TODO: implement Page8 flow per architecture doc section 3 —
# track active sessions via Redis, subscribe pub/sub for online-count and
# per-service health, push to connected WebSocket clients.
