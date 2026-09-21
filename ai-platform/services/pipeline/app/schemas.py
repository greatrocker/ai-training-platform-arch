import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LogicFlowIn(BaseModel):
    name: str
    graph_json: str = Field(description="JSON-encoded {nodes:[...], edges:[...]} from the node-graph editor")


class LogicFlowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    flow_id: uuid.UUID
    name: str | None
    graph_json: str | None
    created_by: str | None
    updated_at: datetime | None


class CctvDeviceIn(BaseModel):
    device_name: str
    rtsp_url: str
    username: str | None = None
    password: str | None = None
    bound_flow_id: uuid.UUID | None = None


class CctvDeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    device_id: uuid.UUID
    device_name: str | None
    rtsp_url: str | None
    username: str | None
    bound_flow_id: uuid.UUID | None
    status: str | None


class SnapshotResult(BaseModel):
    ok: bool
    snapshot_url: str | None = None
    error: str | None = None
