import re
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..crypto import decrypt_password, encrypt_password
from ..db import get_db
from ..storage import presigned_snapshot_url, upload_snapshot

router = APIRouter(prefix="/api/pipeline/devices", tags=["cctv-devices"])


def _out(device: models.CctvDevice) -> schemas.CctvDeviceOut:
    return schemas.CctvDeviceOut.model_validate(device)


@router.get("", response_model=list[schemas.CctvDeviceOut])
def list_devices(db: Session = Depends(get_db)):
    return [_out(d) for d in db.query(models.CctvDevice).all()]


@router.post("", response_model=schemas.CctvDeviceOut, status_code=201)
def create_device(payload: schemas.CctvDeviceIn, db: Session = Depends(get_db)):
    device = models.CctvDevice(
        device_name=payload.device_name,
        rtsp_url=payload.rtsp_url,
        username=payload.username,
        password_encrypted=encrypt_password(payload.password) if payload.password else None,
        bound_flow_id=payload.bound_flow_id,
        status="inactive",
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return _out(device)


@router.get("/{device_id}", response_model=schemas.CctvDeviceOut)
def get_device(device_id: uuid.UUID, db: Session = Depends(get_db)):
    device = db.get(models.CctvDevice, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="device not found")
    return _out(device)


@router.put("/{device_id}", response_model=schemas.CctvDeviceOut)
def update_device(device_id: uuid.UUID, payload: schemas.CctvDeviceIn, db: Session = Depends(get_db)):
    device = db.get(models.CctvDevice, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="device not found")
    device.device_name = payload.device_name
    device.rtsp_url = payload.rtsp_url
    device.username = payload.username
    if payload.password:
        device.password_encrypted = encrypt_password(payload.password)
    device.bound_flow_id = payload.bound_flow_id
    db.commit()
    db.refresh(device)
    return _out(device)


@router.delete("/{device_id}", status_code=204)
def delete_device(device_id: uuid.UUID, db: Session = Depends(get_db)):
    device = db.get(models.CctvDevice, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="device not found")
    db.delete(device)
    db.commit()


def _clean_ffmpeg_error(stderr: str, password: str | None) -> str:
    # ffmpeg's own error output echoes back the full URL it tried, which
    # includes the plaintext password — strip both the exact secret and
    # any generic userinfo@ segment so nothing leaks through the API.
    # Also drop the boilerplate build-config banner so only the lines that
    # actually explain the failure come through.
    if password:
        stderr = stderr.replace(password, "***")
    stderr = re.sub(r"://([^/@\s]+)@", "://***@", stderr)
    keep = [
        line for line in stderr.splitlines()
        if line.strip() and not line.lstrip().startswith(("--enable", "--disable", "configuration:", "built with"))
        and not re.match(r"^\s*lib\w+\s+\d+\.", line)
    ]
    return "\n".join(keep[-15:])


def _build_authenticated_url(rtsp_url: str, username: str | None, password: str | None) -> str:
    if not username:
        return rtsp_url
    parts = urlsplit(rtsp_url)
    userinfo = username if not password else f"{username}:{password}"
    netloc = f"{userinfo}@{parts.hostname or ''}"
    if parts.port:
        netloc += f":{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


@router.post("/{device_id}/snapshot-test", response_model=schemas.SnapshotResult)
def snapshot_test(device_id: uuid.UUID, db: Session = Depends(get_db)):
    device = db.get(models.CctvDevice, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="device not found")

    password = decrypt_password(device.password_encrypted) if device.password_encrypted else None
    url = _build_authenticated_url(device.rtsp_url, device.username, password)

    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "snapshot.jpg"
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-rtsp_transport", "tcp",
                "-timeout", "5000000",  # microseconds, ffmpeg's socket timeout for the RTSP connection
                "-i", url,
                "-frames:v", "1",
                "-q:v", "2",
                str(out_path),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0 or not out_path.exists():
            device.status = "error"
            db.commit()
            error = _clean_ffmpeg_error(result.stderr, password) or "ffmpeg failed to capture a frame"
            return schemas.SnapshotResult(ok=False, error=error)

        object_name = f"{device_id}/{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.jpg"
        upload_snapshot(object_name, str(out_path))

    device.status = "active"
    db.commit()
    return schemas.SnapshotResult(ok=True, snapshot_url=presigned_snapshot_url(object_name))
