from __future__ import annotations

from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile

from .model import Device
from .safety import SafetyError, require_directory
from .ssh import read_authorized_key


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _copy_required(source: Path, destination: Path, mode: int) -> None:
    if not source.is_file():
        raise SafetyError(f"required runtime binary is not readable: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    destination.chmod(mode)


def _extract_nickelmenu(package: Path, root: Path) -> None:
    if not package.is_file():
        raise SafetyError(f"NickelMenu package is not readable: {package}")
    with tarfile.open(package, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            path = PurePosixPath(member.name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or not (member.isfile() or member.isdir())
            ):
                raise SafetyError(
                    f"NickelMenu package contains an unsafe member: {member.name}"
                )
        archive.extractall(root, members=members)
    if not (root / "usr/local/Kobo/imageformats/libnm.so").is_file():
        raise SafetyError("NickelMenu package does not contain libnm.so")


def _build_nickelmenu_tree(
    template: Path, root: Path, package: Path, hostname: str
) -> None:
    hosts = template / "etc/hosts"
    if not hosts.is_file():
        raise SafetyError(f"adapter rootfs has no hosts policy: {hosts}")
    (root / "etc").mkdir(parents=True)
    shutil.copy2(hosts, root / "etc/hosts")
    _extract_nickelmenu(package, root)
    _render_hostname(root, hostname)


def _render_hostname(root: Path, hostname: str) -> None:
    for relative in ("etc/hostname", "etc/hosts", "etc/init.d/ssh"):
        path = root / relative
        if not path.is_file():
            continue
        path.write_text(
            path.read_text(encoding="utf-8").replace("@HOSTNAME@", hostname),
            encoding="utf-8",
        )


def _add_tree(archive: tarfile.TarFile, root: Path, epoch: int) -> None:
    entries = [root, *sorted(root.rglob("*"))]
    for path in entries:
        relative = path.relative_to(root)
        arcname = "." if not relative.parts else "./" + relative.as_posix()
        info = archive.gettarinfo(str(path), arcname=arcname)
        info.uid = 0
        info.gid = 0
        info.uname = "root"
        info.gname = "root"
        info.mtime = epoch
        if path.is_dir():
            archive.addfile(info)
        elif path.is_file():
            with path.open("rb") as handle:
                archive.addfile(info, handle)
        else:
            raise SafetyError(f"unsupported root package entry: {path}")


def build_kobo_root(
    *,
    device: Device,
    adapter_rootfs: Path,
    authorized_key: Path | None = None,
    scp_binary: Path | None = None,
    sftp_server_binary: Path | None = None,
    rsync_binary: Path | None = None,
    output_directory: Path,
    launch_mode: str = "autostart",
    nickelmenu_package: Path | None = None,
) -> dict[str, str]:
    if device.platform != "kobo":
        raise SafetyError(f"Kobo root builder cannot build adapter {device.id}")
    if launch_mode not in {"autostart", "nickelmenu"}:
        raise SafetyError(f"unsupported KOReader launch mode: {launch_mode}")
    template = require_directory(adapter_rootfs, "adapter rootfs")
    output_directory = output_directory.expanduser().resolve()
    output_directory.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="koreader-appliance-root-") as temporary:
        work = Path(temporary)
        root = work / "rootfs"
        public_key = None
        host_public_key = None
        if launch_mode == "nickelmenu":
            if nickelmenu_package is None:
                raise SafetyError("nickelmenu mode requires --nickelmenu-package")
            _build_nickelmenu_tree(
                template,
                root,
                nickelmenu_package.expanduser().resolve(),
                device.ssh.hostname,
            )
        else:
            missing = [
                name
                for name, value in (
                    ("authorized key", authorized_key),
                    ("scp", scp_binary),
                    ("sftp-server", sftp_server_binary),
                    ("rsync", rsync_binary),
                )
                if value is None
            ]
            if missing:
                raise SafetyError(
                    "autostart root build requires " + ", ".join(missing)
                )
            public_key = read_authorized_key(authorized_key)  # type: ignore[arg-type]
            shutil.copytree(template, root)
            _render_hostname(root, device.ssh.hostname)

            host_key = work / "ssh_host_ed25519_key"
            subprocess.run(
                [
                    "ssh-keygen",
                    "-q",
                    "-t",
                    "ed25519",
                    "-N",
                    "",
                    "-C",
                    device.id,
                    "-f",
                    str(host_key),
                ],
                check=True,
            )
            host_public_key = host_key.with_suffix(".pub")

            key_targets = [root / path for path in device.ssh.authorized_keys_paths]
            for target in key_targets:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(public_key, encoding="utf-8")
                target.chmod(0o600)
                target.parent.chmod(0o700)

            ssh_directory = root / "etc" / "ssh"
            ssh_directory.mkdir(parents=True, exist_ok=True)
            shutil.copy2(host_key, ssh_directory / "ssh_host_ed25519_key")
            shutil.copy2(host_public_key, ssh_directory / "ssh_host_ed25519_key.pub")
            (ssh_directory / "ssh_host_ed25519_key").chmod(0o600)
            (ssh_directory / "ssh_host_ed25519_key.pub").chmod(0o644)

            _copy_required(scp_binary, root / "usr" / "bin" / "scp", 0o755)  # type: ignore[arg-type]
            _copy_required(
                sftp_server_binary,  # type: ignore[arg-type]
                root / "usr" / "libexec" / "sftp-server",
                0o755,
            )
            _copy_required(
                rsync_binary,  # type: ignore[arg-type]
                root / "mnt" / "onboard" / ".adds" / "koreader" / "rsync",
                0o755,
            )

        epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "0"))
        installer = output_directory / "KoboRoot.tgz"
        with installer.open("wb") as raw:
            with gzip.GzipFile(
                filename="KoboRoot.tar", mode="wb", fileobj=raw, mtime=epoch
            ) as compressed:
                with tarfile.open(
                    fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT
                ) as archive:
                    _add_tree(archive, root, epoch)

        exported_public_key = None
        fingerprint = "not-applicable"
        if host_public_key is not None:
            exported_public_key = output_directory / "device-host-ed25519.pub"
            shutil.copy2(host_public_key, exported_public_key)
            fingerprint = subprocess.run(
                ["ssh-keygen", "-E", "sha256", "-lf", str(exported_public_key)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        manifest = {
            "schema": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "device": device.id,
            "launch_mode": launch_mode,
            "installer": installer.name,
            "installer_sha256": _sha256(installer),
            "host_public_key": exported_public_key.name
            if exported_public_key is not None
            else None,
            "host_fingerprint": fingerprint,
            "authorized_key_sha256": hashlib.sha256(public_key.encode()).hexdigest()
            if public_key is not None
            else None,
            "runtime_binaries": {
                "scp": _sha256(scp_binary) if scp_binary is not None else None,
                "sftp_server": _sha256(sftp_server_binary)
                if sftp_server_binary is not None
                else None,
                "rsync": _sha256(rsync_binary) if rsync_binary is not None else None,
            },
            "nickelmenu_package_sha256": _sha256(nickelmenu_package)
            if nickelmenu_package is not None
            else None,
        }
        manifest_path = output_directory / "build-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        return {
            "installer": str(installer),
            "installer_sha256": str(manifest["installer_sha256"]),
            "host_public_key": str(exported_public_key)
            if exported_public_key is not None
            else "not-applicable",
            "host_fingerprint": fingerprint,
            "manifest": str(manifest_path),
        }
