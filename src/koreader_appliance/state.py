from __future__ import annotations

from pathlib import Path

from .backup import verify_backup_manifest
from .manifest import ApplianceManifest
from .model import Device
from .safety import SafetyError, require_directory, under
from .stage import stage_koreader


def require_installable(device: Device, allow_unverified: bool = False) -> None:
    if device.platform != "kobo":
        raise SafetyError(
            f"cannot apply {device.id}: Kindle and other non-Kobo readers need "
            "a vendor adapter and jailbreak (KUAL/MRPI), not KoboRoot.tgz"
        )
    if device.status == "unverified" and not allow_unverified:
        raise SafetyError(
            f"{device.id} is unverified on hardware (status: {device.status}); "
            "pass --allow-unverified to permit staging"
        )


def _step(action: str, target: Path, status: str) -> dict[str, str]:
    return {"action": action, "target": str(target), "status": status}


def plan(
    mount: Path, manifest: ApplianceManifest, device: Device
) -> list[dict[str, str]]:
    mount = require_directory(mount, "reader mount")
    koreader_root = under(mount, device.storage.koreader_root)
    settings = koreader_root / "settings.reader.lua.pending"
    books_root = under(mount, device.storage.books_root)
    trigger = (
        under(mount, device.storage.installer_trigger)
        if device.storage.installer_trigger
        else None
    )

    steps = [
        _step(
            "koreader-root",
            koreader_root,
            "ok" if (koreader_root / "reader.lua").is_file() else "pending",
        ),
    ]
    if trigger is not None:
        steps.append(
            _step(
                "installer-trigger",
                trigger,
                "ok"
                if trigger.is_file()
                and ApplianceManifest.hash_file(trigger)
                == manifest.root_package.sha256
                else "pending",
            )
        )
    if manifest.settings is not None:
        steps.append(
            _step(
                "settings-profile",
                settings,
                "ok" if settings.is_file() else "pending",
            )
        )
    steps.extend(
        _step(
            "library-folder",
            books_root / folder,
            "ok" if (books_root / folder).is_dir() else "pending",
        )
        for folder in manifest.library.folders
    )
    if device.platform == "kobo":
        ssh_marker = under(mount, ".kobo/ssh-enabled")
        steps.append(
            _step(
                "ssh-enabled-marker",
                ssh_marker,
                "ok" if ssh_marker.is_file() else "pending",
            )
        )
    return steps


def _verify_pin(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise SafetyError(f"{label} is not a readable file: {path}")
    actual = ApplianceManifest.hash_file(path)
    if actual != expected:
        raise SafetyError(
            f"{label} SHA-256 mismatch: expected {expected}, got {actual}"
        )


def apply(
    mount: Path,
    manifest: ApplianceManifest,
    device: Device,
    allow_unverified: bool = False,
) -> list[dict[str, str]]:
    mount = require_directory(mount, "reader mount")
    require_installable(device, allow_unverified)
    if not device.matches(mount):
        raise SafetyError(f"{mount} does not match adapter {device.id}")
    if manifest.device != device.id:
        raise SafetyError(
            f"appliance manifest targets {manifest.device}, detected {device.id}"
        )
    verify_backup_manifest(manifest.backup.manifest, device, mount)
    _verify_pin(manifest.koreader.path, manifest.koreader.sha256, "KOReader archive")
    _verify_pin(manifest.root_package.path, manifest.root_package.sha256, "root package")

    before = plan(mount, manifest, device)
    if any(step["status"] == "pending" for step in before):
        stage_koreader(
            mount,
            manifest.koreader.path,
            manifest.root_package.path,
            device,
            manifest.settings.profile if manifest.settings is not None else None,
            manifest.library.folders,
        )
    return plan(mount, manifest, device)
