from __future__ import annotations

from pathlib import Path

from .backup import verify_backup_manifest
from .manifest import ApplianceManifest
from .model import Device
from .safety import SafetyError, require_directory, under
from .stage import (
    EXCLUDE_SYNC_FOLDERS,
    NICKELMENU_CONFIG,
    NICKELMENU_LAUNCHER,
    deployment_is_current,
    library_is_current,
    stage_koreader,
)
from .ssh import read_authorized_key


def require_installable(device: Device, allow_unverified: bool = False) -> None:
    if device.platform != "kobo":
        raise SafetyError(
            f"cannot apply {device.id}: Kindle and other non-Kobo readers need "
            "a vendor adapter and jailbreak (KUAL/MRPI), not KoboRoot.tgz"
        )
    if device.status == "blocked":
        raise SafetyError(
            f"{device.id} is blocked; installation is not available for this adapter"
        )
    if device.status != "verified" and not allow_unverified:
        raise SafetyError(
            f"{device.id} is not verified on hardware (status: {device.status}); "
            "pass --allow-unverified to permit staging"
        )


def _step(action: str, target: Path, status: str) -> dict[str, str]:
    return {"action": action, "target": str(target), "status": status}


def _backup_state(
    manifest: ApplianceManifest, device: Device
) -> tuple[Path | None, str | None]:
    backup_manifest = manifest.backup.manifest
    if not backup_manifest.is_file():
        return None, None
    state_source = under(backup_manifest.parent, device.storage.koreader_root)
    return (
        state_source if state_source.is_dir() else None,
        ApplianceManifest.hash_file(backup_manifest),
    )


def plan(
    mount: Path, manifest: ApplianceManifest, device: Device
) -> list[dict[str, str]]:
    mount = require_directory(mount, "reader mount")
    koreader_root = under(mount, device.storage.koreader_root)
    settings = koreader_root / (
        "settings.reader.lua.pending"
        if manifest.launch.mode == "autostart"
        else "settings.reader.lua"
    )
    books_root = under(mount, device.storage.books_root)
    trigger = (
        under(mount, device.storage.installer_trigger)
        if device.storage.installer_trigger
        else None
    )
    _, state_backup_sha256 = _backup_state(manifest, device)

    steps = [
        _step(
            "koreader-root",
            koreader_root,
            "ok"
            if deployment_is_current(
                koreader_root,
                device,
                manifest.koreader.sha256,
                manifest.launch.mode,
                manifest.syncthing.plugin.sha256 if manifest.syncthing else None,
                manifest.syncthing.binary.sha256 if manifest.syncthing else None,
                state_backup_sha256,
            )
            else "pending",
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
    if manifest.ssh is not None:
        authorized_keys = koreader_root / "settings/SSH/authorized_keys"
        expected_key = (
            read_authorized_key(manifest.ssh.authorized_key)
            if manifest.ssh.authorized_key.is_file()
            else None
        )
        steps.append(
            _step(
                "ssh-authorized-key",
                authorized_keys,
                "ok"
                if expected_key is not None
                and authorized_keys.is_file()
                and authorized_keys.read_text(encoding="utf-8") == expected_key
                else "pending",
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
    if manifest.library.sha256 is not None:
        steps.append(
            _step(
                "library-restore",
                books_root,
                "ok"
                if library_is_current(mount, manifest.library.sha256)
                else "pending",
            )
        )
    if device.platform == "kobo" and manifest.launch.mode == "autostart":
        ssh_marker = under(mount, ".kobo/ssh-enabled")
        steps.append(
            _step(
                "ssh-enabled-marker",
                ssh_marker,
                "ok" if ssh_marker.is_file() else "pending",
            )
        )
    if device.platform == "kobo" and manifest.launch.mode == "nickelmenu":
        launcher = under(mount, ".adds/nm/koreader")
        launcher_script = under(
            mount, ".adds/koreader-appliance/koreader-launch.sh"
        )
        config = under(mount, ".kobo/Kobo/Kobo eReader.conf")
        steps.append(
            _step(
                "nickelmenu-launcher",
                launcher,
                "ok"
                if launcher.is_file()
                and launcher.read_text(encoding="utf-8") == NICKELMENU_CONFIG
                and launcher_script.is_file()
                and launcher_script.read_text(encoding="utf-8")
                == NICKELMENU_LAUNCHER
                and config.is_file()
                and f"ExcludeSyncFolders={EXCLUDE_SYNC_FOLDERS}\n"
                in config.read_text(encoding="utf-8")
                else "pending",
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
    state_source, state_backup_sha256 = _backup_state(manifest, device)
    _verify_pin(manifest.koreader.path, manifest.koreader.sha256, "KOReader archive")
    _verify_pin(manifest.root_package.path, manifest.root_package.sha256, "root package")
    if manifest.syncthing is not None:
        _verify_pin(
            manifest.syncthing.plugin.path,
            manifest.syncthing.plugin.sha256,
            "Syncthing plugin archive",
        )
        _verify_pin(
            manifest.syncthing.binary.path,
            manifest.syncthing.binary.sha256,
            "Syncthing binary archive",
        )

    before = plan(mount, manifest, device)
    if any(step["status"] == "pending" for step in before):
        stage_koreader(
            mount,
            manifest.koreader.path,
            manifest.root_package.path,
            device,
            manifest.settings.profile if manifest.settings is not None else None,
            manifest.library.folders,
            manifest.launch.mode,
            manifest.ssh.authorized_key if manifest.ssh is not None else None,
            manifest.library.restore,
            manifest.library.sha256,
            manifest.syncthing.plugin.path if manifest.syncthing else None,
            manifest.syncthing.binary.path if manifest.syncthing else None,
            state_source,
            state_backup_sha256,
        )
    return plan(mount, manifest, device)
