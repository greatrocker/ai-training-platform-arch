import uuid
from datetime import datetime

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class AlarmEvent(Base):
    __tablename__ = "alarm_event"
    alarm_id: Mapped[uuid.UUID] = mapped_column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(UNIQUEIDENTIFIER, nullable=True)  # cross-service ref
    flow_id: Mapped[uuid.UUID] = mapped_column(UNIQUEIDENTIFIER, nullable=True)    # cross-service ref
    snapshot_path: Mapped[str] = mapped_column(String(500), nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(nullable=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
