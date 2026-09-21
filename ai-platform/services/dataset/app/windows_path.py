"""Translate a Windows path the user typed (e.g. D:\\Videos\\lineA) into
the path it appears at inside this container, where each mounted drive
letter is bind-mounted read-only at /mnt/host/<letter> (see
docker-compose.yml + WINDOWS_DRIVE_MOUNTS)."""

import re
from pathlib import Path

_DRIVE_RE = re.compile(r"^([A-Za-z]):[\\/](.*)$")


class InvalidWindowsPath(ValueError):
    pass


def resolve_windows_path(win_path: str, mounted_drives: set[str]) -> Path:
    match = _DRIVE_RE.match(win_path.strip())
    if not match:
        raise InvalidWindowsPath(
            "path must be an absolute Windows path, e.g. D:\\Videos\\lineA"
        )

    drive, rest = match.group(1).lower(), match.group(2)
    if drive not in mounted_drives:
        mounted = ", ".join(sorted(d.upper() for d in mounted_drives)) or "(none)"
        raise InvalidWindowsPath(
            f"drive {drive.upper()}: is not mounted into the container — mounted drives: {mounted}. "
            "Add it to WINDOWS_DRIVE_MOUNTS and docker-compose.yml volumes."
        )

    rest = rest.replace("\\", "/")
    container_root = Path(f"/mnt/host/{drive}")
    candidate = (container_root / rest).resolve()

    if candidate != container_root and container_root not in candidate.parents:
        raise InvalidWindowsPath("path escapes the mounted drive")

    return candidate
