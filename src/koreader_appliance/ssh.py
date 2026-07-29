from __future__ import annotations

from pathlib import Path
import shlex
import subprocess

from .model import Device
from .safety import SafetyError


def read_authorized_key(path: Path) -> str:
    source = path.expanduser().resolve()
    if not source.is_file():
        raise SafetyError(f"authorized public key is not readable: {source}")
    lines = [
        line.strip()
        for line in source.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not lines or any(
        not line.startswith(("ssh-", "sk-ssh-", "ecdsa-")) for line in lines
    ):
        raise SafetyError(
            "authorized key file must contain only OpenSSH public keys"
        )
    if len(set(lines)) != len(lines):
        raise SafetyError("authorized key file contains duplicate public keys")
    return "\n".join(lines) + "\n"


def public_key_and_fingerprint(path: Path) -> tuple[str, str]:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise SafetyError(f"host public key is not readable: {path}")
    key = path.read_text(encoding="utf-8").strip()
    fields = key.split()
    if len(fields) < 2:
        raise SafetyError(f"invalid OpenSSH host public key: {path}")
    fingerprint = subprocess.run(
        ["ssh-keygen", "-E", "sha256", "-lf", str(path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return " ".join(fields[:2]), fingerprint


def render_host_config(
    device: Device,
    host_public_key: Path,
    identity_file: Path,
    alias: str,
    hostname: str,
) -> str:
    public_key, fingerprint = public_key_and_fingerprint(host_public_key)
    host_key_alias = f"{alias}-koreader"
    known_hosts = f"{host_key_alias} {public_key}"
    config = f"""# {device.name}; host fingerprint: {fingerprint}
Host {alias}
  HostName {hostname}
  HostKeyAlias {host_key_alias}
  User {device.ssh.user}
  Port {device.ssh.port}
  IdentityFile {shlex.quote(str(identity_file.expanduser()))}
  IdentitiesOnly yes
  PreferredAuthentications publickey
  PasswordAuthentication no
  KbdInteractiveAuthentication no
  StrictHostKeyChecking yes
  UserKnownHostsFile ~/.ssh/{alias}-known-hosts
  ForwardAgent no
  ClearAllForwardings yes
  ControlMaster no
  ControlPath none
  ControlPersist no
"""
    return (
        config + f"\n# Write this line to ~/.ssh/{alias}-known-hosts:\n{known_hosts}\n"
    )
