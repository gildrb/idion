from __future__ import annotations

import os
from pathlib import Path


class SafetyError(ValueError):
    """Raised when a requested filesystem operation crosses a safety boundary."""


def require_directory(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        raise SafetyError(f"{label} is not a directory: {resolved}")
    return resolved


def relative_device_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or not value or ".." in path.parts:
        raise SafetyError(f"device path must be non-empty and relative: {value!r}")
    return path


def under(base: Path, relative: str) -> Path:
    base = base.resolve()
    candidate = (base / relative_device_path(relative)).resolve()
    if candidate != base and base not in candidate.parents:
        raise SafetyError(f"path escapes device root: {relative!r}")
    return candidate


def require_outside(candidate: Path, protected: Path, label: str) -> Path:
    candidate = candidate.expanduser().resolve()
    protected = protected.expanduser().resolve()
    if candidate == protected or protected in candidate.parents:
        raise SafetyError(f"{label} must be outside {protected}")
    return candidate


def fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
