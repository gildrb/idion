from __future__ import annotations

from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

from .model import Device
from .safety import SafetyError, require_directory


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_public_key(path: Path) -> str:
    if not path.is_file():
        raise SafetyError(f"authorized public key is not readable: {path}")
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(lines) != 1 or not lines[0].startswith(("ssh-", "sk-ssh-", "ecdsa-")):
        raise SafetyError(
            "authorized key file must contain exactly one OpenSSH public key"
        )
    return lines[0] + "\n"


def _copy_required(source: Path, destination: Path, mode: int) -> None:
    if not source.is_file():
        raise SafetyError(f"required runtime binary is not readable: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    destination.chmod(mode)


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
    authorized_key: Path,
    scp_binary: Path,
    sftp_server_binary: Path,
    rsync_binary: Path,
    output_directory: Path,
) -> dict[str, str]:
    if device.platform != "kobo":
        raise SafetyError(f"Kobo root builder cannot build adapter {device.id}")
    template = require_directory(adapter_rootfs, "adapter rootfs")
    public_key = _read_public_key(authorized_key.expanduser().resolve())
    output_directory = output_directory.expanduser().resolve()
    output_directory.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="koreader-appliance-root-") as temporary:
        work = Path(temporary)
        root = work / "rootfs"
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

        _copy_required(scp_binary, root / "usr" / "bin" / "scp", 0o755)
        _copy_required(
            sftp_server_binary, root / "usr" / "libexec" / "sftp-server", 0o755
        )
        _copy_required(
            rsync_binary,
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
            "installer": installer.name,
            "installer_sha256": _sha256(installer),
            "host_public_key": exported_public_key.name,
            "host_fingerprint": fingerprint,
            "authorized_key_sha256": hashlib.sha256(public_key.encode()).hexdigest(),
            "runtime_binaries": {
                "scp": _sha256(scp_binary),
                "sftp_server": _sha256(sftp_server_binary),
                "rsync": _sha256(rsync_binary),
            },
        }
        manifest_path = output_directory / "build-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        return {
            "installer": str(installer),
            "installer_sha256": str(manifest["installer_sha256"]),
            "host_public_key": str(exported_public_key),
            "host_fingerprint": fingerprint,
            "manifest": str(manifest_path),
        }
