from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile

from .model import Device
from .safety import SafetyError, fsync_file, require_directory, under


def _safe_zip_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members = archive.infolist()
    for member in members:
        path = PurePosixPath(member.filename)
        if path.is_absolute() or ".." in path.parts:
            raise SafetyError(
                f"archive member escapes extraction root: {member.filename}"
            )
    return members


def _find_koreader_root(extracted: Path) -> Path:
    for candidate in (extracted / ".adds" / "koreader", extracted / "koreader"):
        if (candidate / "reader.lua").is_file():
            return candidate
    matches = [path.parent for path in extracted.rglob("reader.lua")]
    if len(matches) != 1:
        raise SafetyError(
            "KOReader archive does not contain one identifiable reader.lua"
        )
    return matches[0]


def stage_koreader(
    mount: Path,
    archive_path: Path,
    root_package: Path,
    device: Device,
    settings: Path | None = None,
) -> dict[str, str]:
    mount = require_directory(mount, "reader mount")
    if not device.matches(mount):
        raise SafetyError(f"{mount} does not match adapter {device.id}")
    if not archive_path.is_file() or not root_package.is_file():
        raise SafetyError(
            "KOReader archive and root package must both be readable files"
        )

    with tempfile.TemporaryDirectory(prefix="koreader-appliance-stage-") as temporary:
        extracted = Path(temporary)
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(extracted, members=_safe_zip_members(archive))
        source = _find_koreader_root(extracted)
        destination = under(mount, device.storage.koreader_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            source, destination, dirs_exist_ok=True, copy_function=shutil.copy2
        )

    trigger = under(mount, device.storage.installer_trigger)
    trigger.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root_package, trigger)
    fsync_file(trigger)

    source_hash = hashlib.sha256(root_package.read_bytes()).hexdigest()
    staged_hash = hashlib.sha256(trigger.read_bytes()).hexdigest()
    if source_hash != staged_hash:
        raise OSError("root package changed while staging")

    books_root = under(mount, device.storage.books_root)
    for directory in ("Programming", "Linux", "Math", "Papers", "Manuals"):
        (books_root / directory).mkdir(parents=True, exist_ok=True)

    staged_settings = "not-requested"
    if settings is not None:
        settings = settings.expanduser().resolve()
        if not settings.is_file():
            raise SafetyError(f"KOReader settings profile is not readable: {settings}")
        pending = destination / "settings.reader.lua.pending"
        shutil.copy2(settings, pending)
        fsync_file(pending)
        staged_settings = str(pending)

    if device.platform == "kobo":
        ssh_enabled = under(mount, ".kobo/ssh-enabled")
        ssh_enabled.write_text(
            "Key-only SSH enabled by koreader-appliance.\n",
            encoding="utf-8",
        )
        fsync_file(ssh_enabled)
    return {
        "koreader_root": str(destination),
        "installer_trigger": str(trigger),
        "installer_sha256": staged_hash,
        "ssh_enabled_marker": str(ssh_enabled)
        if device.platform == "kobo"
        else "not-applicable",
        "settings_pending": staged_settings,
    }
