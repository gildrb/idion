from __future__ import annotations

import os
from pathlib import Path

from .model import Device
from .safety import SafetyError, require_directory


def default_device_directory() -> Path:
    configured = os.environ.get("KOREADER_APPLIANCE_DEVICES")
    if configured:
        return require_directory(Path(configured), "device directory")

    for parent in Path(__file__).resolve().parents:
        candidate = parent / "adapters"
        if candidate.is_dir():
            return candidate
    candidate = Path.cwd() / "adapters"
    if candidate.is_dir():
        return candidate.resolve()
    raise SafetyError(
        "could not locate device adapters; set KOREADER_APPLIANCE_DEVICES"
    )


def _manifest_paths(directory: Path) -> list[Path]:
    direct = [
        path for path in sorted(directory.glob("*.toml"))
        if not path.name.startswith("_")
    ]
    if direct:
        return direct
    return [
        path
        for path in sorted(directory.glob("*/device.toml"))
        if not path.parent.name.startswith("_")
    ]


class Registry:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = require_directory(
            directory or default_device_directory(), "device directory"
        )
        self._devices = {
            device.id: device
            for path in _manifest_paths(self.directory)
            for device in [Device.from_toml(path)]
        }
        if not self._devices:
            raise SafetyError(f"no device manifests found in {self.directory}")

    def all(self) -> tuple[Device, ...]:
        return tuple(self._devices.values())

    def get(self, device_id: str) -> Device:
        try:
            return self._devices[device_id]
        except KeyError as error:
            raise SafetyError(f"unknown device adapter: {device_id}") from error

    def detect(self, mount: Path) -> Device:
        mount = require_directory(mount, "reader mount")
        matches = [device for device in self.all() if device.matches(mount)]
        if len(matches) != 1:
            names = ", ".join(device.id for device in matches) or "none"
            raise SafetyError(
                f"expected exactly one device match at {mount}; found {names}"
            )
        return matches[0]
