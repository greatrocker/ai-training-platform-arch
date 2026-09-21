import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, LargeBinary, String
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class LogicFlow(Base):
    __tablename__ = "logic_flow"
    flow_id: Mapped[uuid.UUID] = mapped_column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=True)
    graph_json: Mapped[str] = mapped_column(String, nullable=True)
    created_by: Mapped[str] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(nullable=True)


class CctvDevice(Base):
    __tablename__ = "cctv_device"
    device_id: Mapped[uuid.UUID] = mapped_column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    device_name: Mapped[str] = mapped_column(String(100), nullable=True)
    rtsp_url: Mapped[str] = mapped_column(String(500), nullable=True)
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    password_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=True)
    bound_flow_id: Mapped[uuid.UUID] = mapped_column(UNIQUEIDENTIFIER, ForeignKey("logic_flow.flow_id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=True)  # active/inactive/error
