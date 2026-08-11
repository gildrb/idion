from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from .safety import SafetyError


def _run(
    command: list[str], *, input_text: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        input=input_text,
        capture_output=True,
        text=True,
    )


def _effective_ssh(host: str) -> dict[str, list[str]]:
    output = _run(["ssh", "-G", host]).stdout
    settings: dict[str, list[str]] = {}
    for line in output.splitlines():
        key, separator, value = line.partition(" ")
        if separator:
            settings.setdefault(key, []).append(value)
    return settings


def _first(settings: dict[str, list[str]], key: str) -> str:
    values = settings.get(key)
    return values[0] if values else ""


def _fingerprint(value: str) -> str:
    match = re.search(r"SHA256:[A-Za-z0-9+/=]+", value)
    if not match:
        raise SafetyError(f"missing SHA-256 fingerprint in: {value!r}")
    return match.group(0)


def _validate_nickelmenu(
    host: str,
    manifest: dict[str, object],
    evidence: Path,
) -> dict[str, object]:
    passes: list[str] = []
    failures: list[str] = []

    def check(condition: bool, label: str) -> None:
        (passes if condition else failures).append(label)

    settings = _effective_ssh(host)
    policy = {
        "stricthostkeychecking": _first(settings, "stricthostkeychecking"),
        "identitiesonly": _first(settings, "identitiesonly"),
        "passwordauthentication": _first(settings, "passwordauthentication"),
        "kbdinteractiveauthentication": _first(
            settings, "kbdinteractiveauthentication"
        ),
        "forwardagent": _first(settings, "forwardagent"),
        "clearallforwardings": _first(settings, "clearallforwardings"),
        "port": _first(settings, "port"),
    }
    check(
        policy["stricthostkeychecking"] == "true"
        and policy["identitiesonly"] == "yes"
        and policy["passwordauthentication"] == "no"
        and policy["kbdinteractiveauthentication"] == "no"
        and policy["forwardagent"] == "no"
        and policy["clearallforwardings"] == "yes"
        and policy["port"] == "2222",
        "client SSH policy is pinned, key-only, forwarding-free, and on port 2222",
    )

    known_hosts_values = _first(settings, "userknownhostsfile").split()
    known_hosts = (
        Path(known_hosts_values[0]).expanduser() if known_hosts_values else None
    )
    check(
        known_hosts is not None
        and known_hosts.is_file()
        and bool(
            _run(["ssh-keygen", "-E", "sha256", "-lf", str(known_hosts)]).stdout
        ),
        "KOReader Dropbear host key is pinned locally",
    )

    identity = _run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            host,
            'printf "uid=%s\\n" "$(id -u)"',
        ]
    ).stdout
    check("uid=0\n" in identity, "SSH reaches KOReader's root-owned Dropbear")

    health = _run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            host,
            "cat /mnt/onboard/.adds/koreader/.idion.json; "
            "ps; df -k /mnt/onboard; uptime",
        ]
    ).stdout
    check(
        '"launch_mode": "nickelmenu"' in health
        and '"device": "kobo-clara-bw"' in health
        and "dropbear" in health.lower(),
        "deployment marker and KOReader Dropbear are healthy",
    )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    remote = f"/tmp/idion-{os.getpid()}-{stamp}"
    with tempfile.TemporaryDirectory(
        prefix="idion-validation-"
    ) as temporary:
        local = Path(temporary)
        fixture = local / "fixture.txt"
        fixture.write_text(f"idion-{stamp}\n", encoding="utf-8")
        expected_hash = hashlib.sha256(fixture.read_bytes()).hexdigest()
        try:
            _run(["scp", "-q", "-O", str(fixture), f"{host}:{remote}"])
            downloaded = local / "downloaded.txt"
            _run(["scp", "-q", "-O", f"{host}:{remote}", str(downloaded)])
            check(
                hashlib.sha256(downloaded.read_bytes()).hexdigest()
                == expected_hash,
                "Dropbear SCP round trip preserves bytes",
            )
        finally:
            subprocess.run(
                ["ssh", "-o", "BatchMode=yes", host, f"rm -f {remote}"],
                check=False,
                capture_output=True,
                text=True,
            )

    result: dict[str, object] = {
        "schema": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "host": host,
        "build_installer_sha256": manifest.get("installer_sha256"),
        "passes": passes,
        "failures": failures,
        "health": health.splitlines(),
        "physical_gates": [
            "display and flicker",
            "front-light intensity and warmth",
            "100 cover sleep and wake cycles",
            "100 Bluetooth remote reconnect cycles",
            "page-turn latency",
            "seven-day battery drain",
        ],
    }
    (evidence / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (evidence / "ssh-policy.json").write_text(
        json.dumps(policy, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {"evidence": str(evidence), "passes": len(passes), "failures": failures}


def validate_live(
    host: str, build_manifest: Path, evidence_root: Path
) -> dict[str, object]:
    build_manifest = build_manifest.expanduser().resolve()
    if not build_manifest.is_file():
        raise SafetyError(f"build manifest is not readable: {build_manifest}")
    try:
        manifest = json.loads(build_manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SafetyError(
            f"build manifest is not valid JSON: {build_manifest}: {error}"
        ) from error
    if manifest.get("schema") != 1:
        raise SafetyError(f"unsupported build manifest: {build_manifest}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    evidence = evidence_root.expanduser().resolve() / stamp
    evidence.mkdir(parents=True)
    if manifest.get("launch_mode") == "nickelmenu":
        return _validate_nickelmenu(host, manifest, evidence)
    passes: list[str] = []
    failures: list[str] = []

    def check(condition: bool, label: str) -> None:
        (passes if condition else failures).append(label)

    settings = _effective_ssh(host)
    policy = {
        "hostkeyalias": _first(settings, "hostkeyalias"),
        "stricthostkeychecking": _first(settings, "stricthostkeychecking"),
        "identitiesonly": _first(settings, "identitiesonly"),
        "passwordauthentication": _first(settings, "passwordauthentication"),
        "kbdinteractiveauthentication": _first(
            settings, "kbdinteractiveauthentication"
        ),
        "forwardagent": _first(settings, "forwardagent"),
        "clearallforwardings": _first(settings, "clearallforwardings"),
    }
    check(
        policy["hostkeyalias"] != ""
        and policy["stricthostkeychecking"] == "true"
        and policy["identitiesonly"] == "yes"
        and policy["passwordauthentication"] == "no"
        and policy["kbdinteractiveauthentication"] == "no"
        and policy["forwardagent"] == "no"
        and policy["clearallforwardings"] == "yes",
        "client SSH policy is pinned, key-only, and forwarding-free",
    )

    known_hosts_value = _first(settings, "userknownhostsfile").split()[0]
    known_hosts = Path(known_hosts_value).expanduser()
    if known_hosts.is_file():
        pinned = _run(["ssh-keygen", "-E", "sha256", "-lf", str(known_hosts)]).stdout
        check(
            _fingerprint(pinned) == _fingerprint(str(manifest["host_fingerprint"])),
            "pinned host fingerprint matches the generated installer",
        )
    else:
        check(False, "pinned host fingerprint matches the generated installer")

    identity = _run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            host,
            'printf "uid=%s\\nhostname=%s\\n" "$(id -u)" "$(hostname)"',
        ]
    ).stdout
    check("uid=0\n" in identity, "SSH reaches the root account")

    health = _run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            host,
            "/mnt/onboard/.adds/koreader/tools/clara-health.sh",
        ]
    ).stdout
    check(
        "koreader_pid=missing" not in health
        and "sshd_pid=stopped" not in health
        and "sshd_watchdog_pid=stopped" not in health,
        "KOReader, OpenSSH, and the independent watchdog are healthy",
    )

    remote_hashes_output = _run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            host,
            "sha256sum /usr/bin/scp /usr/libexec/sftp-server /mnt/onboard/.adds/koreader/rsync",
        ]
    ).stdout
    remote_hashes = {
        path: digest
        for line in remote_hashes_output.splitlines()
        for digest, path in [line.split(maxsplit=1)]
    }
    expected = manifest["runtime_binaries"]
    check(
        remote_hashes.get("/usr/bin/scp") == expected["scp"],
        "remote SCP binary matches the build",
    )
    check(
        remote_hashes.get("/usr/libexec/sftp-server") == expected["sftp_server"],
        "remote SFTP binary matches the build",
    )
    check(
        remote_hashes.get("/mnt/onboard/.adds/koreader/rsync") == expected["rsync"],
        "remote rsync binary matches the build",
    )

    remote = f"/tmp/idion-{os.getpid()}-{stamp}"
    with tempfile.TemporaryDirectory(
        prefix="idion-validation-"
    ) as temporary:
        local = Path(temporary)
        fixture = local / "fixture.txt"
        fixture.write_text(f"idion-{stamp}\n")
        expected_hash = hashlib.sha256(fixture.read_bytes()).hexdigest()
        _run(["ssh", "-o", "BatchMode=yes", host, f"mkdir -p {remote}/rsync"])
        try:
            sftp_batch = f"put {fixture} {remote}/sftp.txt\nget {remote}/sftp.txt {local / 'sftp.txt'}\n"
            _run(["sftp", "-q", "-b", "-", host], input_text=sftp_batch)
            check(
                hashlib.sha256((local / "sftp.txt").read_bytes()).hexdigest()
                == expected_hash,
                "SFTP round trip preserves bytes",
            )

            _run(["scp", "-q", "-O", str(fixture), f"{host}:{remote}/scp.txt"])
            _run(
                ["scp", "-q", "-O", f"{host}:{remote}/scp.txt", str(local / "scp.txt")]
            )
            check(
                hashlib.sha256((local / "scp.txt").read_bytes()).hexdigest()
                == expected_hash,
                "legacy SCP round trip preserves bytes",
            )

            source = local / "source"
            destination = local / "destination"
            source.mkdir()
            destination.mkdir()
            (source / "book.epub").write_bytes(fixture.read_bytes())
            _run(
                [
                    "ssh",
                    "-o",
                    "BatchMode=yes",
                    host,
                    f"printf keep > {remote}/rsync/keep.txt",
                ]
            )
            _run(
                [
                    "rsync",
                    "--archive",
                    "--rsync-path=/usr/bin/rsync",
                    "-e",
                    "ssh -o BatchMode=yes",
                    str(source) + "/",
                    f"{host}:{remote}/rsync/",
                ]
            )
            _run(
                [
                    "rsync",
                    "--archive",
                    "--rsync-path=/usr/bin/rsync",
                    "-e",
                    "ssh -o BatchMode=yes",
                    f"{host}:{remote}/rsync/",
                    str(destination) + "/",
                ]
            )
            check(
                (destination / "keep.txt").is_file()
                and hashlib.sha256((destination / "book.epub").read_bytes()).hexdigest()
                == expected_hash,
                "rsync round trip is byte-exact and additive",
            )
        finally:
            subprocess.run(
                ["ssh", "-o", "BatchMode=yes", host, f"rm -rf {remote}"],
                check=False,
                capture_output=True,
                text=True,
            )

    result: dict[str, object] = {
        "schema": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "host": host,
        "passes": passes,
        "failures": failures,
        "health": health.splitlines(),
        "physical_gates": [
            "display and flicker",
            "front-light intensity and warmth",
            "cover sleep and wake",
            "Bluetooth remote reconnect",
            "subjective page-turn latency",
            "multi-day battery drain",
        ],
    }
    (evidence / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    (evidence / "ssh-policy.json").write_text(
        json.dumps(policy, indent=2, sort_keys=True) + "\n"
    )
    return {"evidence": str(evidence), "passes": len(passes), "failures": failures}
