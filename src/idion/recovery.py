from __future__ import annotations

from pathlib import Path

from .model import Device
from .safety import SafetyError, require_directory, under


def set_autostart_disabled(mount: Path, device: Device, disabled: bool) -> Path:
    mount = require_directory(mount, "reader mount")
    if not device.matches(mount):
        raise SafetyError(f"{mount} does not match adapter {device.id}")
    marker = under(mount, device.storage.recovery_marker)
    if disabled:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(
            "KOReader autostart disabled by idion recovery.\n",
            encoding="utf-8",
        )
    else:
        marker.unlink(missing_ok=True)
    return marker
