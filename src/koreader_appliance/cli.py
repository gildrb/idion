from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from .backup import create_backup, verify_backup_manifest
from .profiles import apply_manga_profile
from .recovery import set_autostart_disabled
from .registry import Registry
from .rootfs import build_kobo_root
from .safety import SafetyError
from .ssh import render_host_config
from .stage import stage_koreader
from .validate import validate_live


def _registry(arguments: argparse.Namespace) -> Registry:
    return Registry(arguments.device_dir)


def _device(arguments: argparse.Namespace):
    registry = _registry(arguments)
    if getattr(arguments, "device", None) == "auto":
        return registry.detect(arguments.mount)
    return registry.get(arguments.device)


def _json(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def devices_command(arguments: argparse.Namespace) -> None:
    _json(
        [
            {
                "id": device.id,
                "name": device.name,
                "platform": device.platform,
                "status": device.status,
            }
            for device in _registry(arguments).all()
        ]
    )


def detect_command(arguments: argparse.Namespace) -> None:
    device = _registry(arguments).detect(arguments.mount)
    _json({"id": device.id, "name": device.name, "status": device.status})


def backup_command(arguments: argparse.Namespace) -> None:
    device = _device(arguments)
    manifest = create_backup(arguments.mount, arguments.destination, device)
    _json({key: manifest[key] for key in ("device", "file_count", "total_bytes")})


def build_root_command(arguments: argparse.Namespace) -> None:
    registry = _registry(arguments)
    device = registry.get(arguments.device)
    repository = Path(__file__).resolve().parents[2]
    adapter_rootfs = repository / "adapters" / device.id / "rootfs"
    _json(
        build_kobo_root(
            device=device,
            adapter_rootfs=adapter_rootfs,
            authorized_key=arguments.authorized_key,
            scp_binary=arguments.scp,
            sftp_server_binary=arguments.sftp_server,
            rsync_binary=arguments.rsync,
            output_directory=arguments.output,
        )
    )


def stage_command(arguments: argparse.Namespace) -> None:
    device = _device(arguments)
    verify_backup_manifest(arguments.backup_manifest, device, arguments.mount)
    settings = arguments.settings
    if settings is None:
        repository = Path(__file__).resolve().parents[2]
        candidate = repository / "profiles" / device.id / "base.lua"
        settings = candidate if candidate.is_file() else None
    _json(
        stage_koreader(
            arguments.mount,
            arguments.koreader,
            arguments.root_package,
            device,
            settings,
        )
    )


def recovery_command(arguments: argparse.Namespace) -> None:
    if not arguments.yes:
        raise SafetyError("recovery marker changes require --yes")
    device = _device(arguments)
    marker = set_autostart_disabled(
        arguments.mount, device, arguments.state == "disable"
    )
    _json({"marker": str(marker), "autostart_disabled": arguments.state == "disable"})


def manga_command(arguments: argparse.Namespace) -> None:
    if not arguments.confirm_closed:
        raise SafetyError("close the document in KOReader, then pass --confirm-closed")
    backup = apply_manga_profile(arguments.sidecar, crop=arguments.crop)
    _json({"sidecar": str(arguments.sidecar.resolve()), "backup": str(backup)})


def ssh_config_command(arguments: argparse.Namespace) -> None:
    device = _registry(arguments).get(arguments.device)
    print(
        render_host_config(
            device,
            arguments.host_public_key,
            arguments.identity_file,
            arguments.alias,
            arguments.hostname,
        ),
        end="",
    )


def validate_command(arguments: argparse.Namespace) -> None:
    result = validate_live(arguments.host, arguments.build_manifest, arguments.evidence)
    _json(result)
    if result["failures"]:
        raise SafetyError("one or more live validation checks failed")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="koreader-appliance")
    result.add_argument(
        "--device-dir", type=Path, help="directory containing device TOML files"
    )
    commands = result.add_subparsers(dest="command", required=True)

    devices = commands.add_parser("devices", help="list known device adapters")
    devices.set_defaults(handler=devices_command)

    detect = commands.add_parser(
        "detect", help="identify a mounted reader without changing it"
    )
    detect.add_argument("mount", type=Path)
    detect.set_defaults(handler=detect_command)

    backup = commands.add_parser(
        "backup", help="copy and hash every accessible storage file"
    )
    backup.add_argument("mount", type=Path)
    backup.add_argument("destination", type=Path)
    backup.add_argument("--device", default="auto")
    backup.set_defaults(handler=backup_command)

    root = commands.add_parser(
        "build-kobo-root", help="build a keyed Kobo root installer"
    )
    root.add_argument("--device", default="kobo-clara-bw")
    root.add_argument("--authorized-key", type=Path, required=True)
    root.add_argument("--scp", type=Path, required=True)
    root.add_argument("--sftp-server", type=Path, required=True)
    root.add_argument("--rsync", type=Path, required=True)
    root.add_argument("--output", type=Path, required=True)
    root.set_defaults(handler=build_root_command)

    stage = commands.add_parser(
        "stage", help="stage KOReader and a root installer on a mounted reader"
    )
    stage.add_argument("mount", type=Path)
    stage.add_argument("--device", default="auto")
    stage.add_argument("--koreader", type=Path, required=True)
    stage.add_argument("--root-package", type=Path, required=True)
    stage.add_argument("--backup-manifest", type=Path, required=True)
    stage.add_argument("--settings", type=Path)
    stage.set_defaults(handler=stage_command)

    recovery = commands.add_parser(
        "recovery", help="enable or remove the autostart recovery marker"
    )
    recovery.add_argument("mount", type=Path)
    recovery.add_argument("state", choices=("disable", "enable"))
    recovery.add_argument("--device", default="auto")
    recovery.add_argument("--yes", action="store_true")
    recovery.set_defaults(handler=recovery_command)

    manga = commands.add_parser(
        "manga-profile", help="make one closed PDF sidecar use whole-page turns"
    )
    manga.add_argument("sidecar", type=Path)
    manga.add_argument(
        "--crop",
        action="store_true",
        help="crop detected margins while fitting the full content",
    )
    manga.add_argument("--confirm-closed", action="store_true")
    manga.set_defaults(handler=manga_command)

    ssh_config = commands.add_parser(
        "ssh-config", help="render a pinned key-only host profile"
    )
    ssh_config.add_argument("--device", default="kobo-clara-bw")
    ssh_config.add_argument("--host-public-key", type=Path, required=True)
    ssh_config.add_argument("--identity-file", type=Path, required=True)
    ssh_config.add_argument("--alias", default="clara")
    ssh_config.add_argument("--hostname", default="clara")
    ssh_config.set_defaults(handler=ssh_config_command)

    validate = commands.add_parser(
        "validate-live",
        help="prove SSH health, hashes, and transfer behavior without rebooting",
    )
    validate.add_argument("--host", default="clara")
    validate.add_argument("--build-manifest", type=Path, required=True)
    validate.add_argument("--evidence", type=Path, required=True)
    validate.set_defaults(handler=validate_command)
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        arguments.handler(arguments)
        return 0
    except (OSError, SafetyError, subprocess.SubprocessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
