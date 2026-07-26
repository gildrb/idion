from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil

from .model import Device
from .safety import SafetyError, fsync_directory, require_directory, require_outside


TRANSIENT_TOP_LEVEL = {
    ".Spotlight-V100",
    ".TemporaryItems",
    ".Trashes",
    ".fseventsd",
}


def _ignored(relative: Path) -> bool:
    if relative.parts and relative.parts[0] in TRANSIENT_TOP_LEVEL:
        return True
    return relative.name == ".DS_Store" or relative.name.startswith("._")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def create_backup(mount: Path, destination: Path, device: Device) -> dict[str, object]:
    mount = require_directory(mount, "reader mount")
    destination = require_outside(destination, mount, "backup destination")
    if destination.exists():
        raise SafetyError(f"backup destination already exists: {destination}")

    partial = destination.with_name(destination.name + ".partial")
    if partial.exists():
        raise SafetyError(f"incomplete backup already exists: {partial}")
    partial.mkdir(parents=True)

    files: list[dict[str, object]] = []
    total_bytes = 0
    try:
        for source in sorted(mount.rglob("*")):
            relative = source.relative_to(mount)
            if _ignored(relative) or source.is_symlink():
                continue
            target = partial / relative
            if source.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not source.is_file():
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            source_hash = sha256_file(source)
            target_hash = sha256_file(target)
            if source_hash != target_hash:
                raise OSError(f"backup verification failed for {relative}")
            size = source.stat().st_size
            total_bytes += size
            files.append(
                {"path": relative.as_posix(), "bytes": size, "sha256": source_hash}
            )

        manifest: dict[str, object] = {
            "schema": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "device": {"id": device.id, "name": device.name},
            "source_mount_name": mount.name,
            "file_count": len(files),
            "total_bytes": total_bytes,
            "excluded_top_level": sorted(TRANSIENT_TOP_LEVEL),
            "files": files,
        }
        manifest_path = partial / "backup-manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        with manifest_path.open("rb") as handle:
            os.fsync(handle.fileno())
        fsync_directory(partial)
        partial.rename(destination)
        fsync_directory(destination.parent)
        return manifest
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise


def verify_backup_manifest(
    manifest_path: Path, device: Device, mount: Path
) -> dict[str, object]:
    manifest_path = require_outside(manifest_path, mount, "backup manifest")
    if not manifest_path.is_file():
        raise SafetyError(f"backup manifest is not readable: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != 1 or manifest.get("device", {}).get("id") != device.id:
        raise SafetyError(
            f"backup manifest does not match {device.id}: {manifest_path}"
        )

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise SafetyError(f"backup manifest contains no files: {manifest_path}")
    backup_root = manifest_path.parent.resolve()
    for record in files:
        if not isinstance(record, dict):
            raise SafetyError(f"invalid backup record in {manifest_path}")
        relative = record.get("path")
        expected = record.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise SafetyError(f"invalid backup record in {manifest_path}")
        candidate = (backup_root / relative).resolve()
        if backup_root not in candidate.parents or not candidate.is_file():
            raise SafetyError(f"backup file is missing or escapes its root: {relative}")
        if sha256_file(candidate) != expected:
            raise SafetyError(f"backup hash mismatch: {relative}")
    return manifest
