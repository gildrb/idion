from __future__ import annotations

from pathlib import Path

from .model import Device
from .safety import SafetyError


def is_bare_profile_name(profile: str | Path) -> bool:
    value = str(profile)
    return len(Path(value).parts) == 1 and not value.startswith((".", "~"))


def adapter_resource(device: Device, relative: str, *, fallback: bool = True) -> Path:
    adapter_root = device.source.parent
    candidate = adapter_root / relative
    if candidate.exists():
        return candidate
    if fallback and device.platform == "kobo":
        candidate = adapter_root.parent / "_kobo-common" / relative
        if candidate.exists():
            return candidate
    raise SafetyError(
        f"could not locate adapter resource {relative!r} for {device.id}; "
        "looked under "
        f"{adapter_root} and "
        f"{adapter_root.parent / '_kobo-common' if device.platform == 'kobo' else 'no shared adapter'}; "
        "the documented install is an editable install from a repository clone, "
        "or set KOREADER_APPLIANCE_DEVICES to an adapter directory"
    )


def settings_profile(device: Device, profile: Path) -> Path:
    profile = profile.expanduser()
    if profile.is_absolute():
        return profile
    if is_bare_profile_name(profile):
        return adapter_resource(device, f"profiles/{profile.name}")
    return profile.resolve()
