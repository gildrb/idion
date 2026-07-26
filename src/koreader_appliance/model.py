from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from .safety import SafetyError, relative_device_path, under


@dataclass(frozen=True)
class Detection:
    required_paths: tuple[str, ...]
    marker_file: str
    marker_tokens: tuple[str, ...]


@dataclass(frozen=True)
class Storage:
    books_root: str
    koreader_root: str
    installer_trigger: str
    recovery_marker: str


@dataclass(frozen=True)
class SSH:
    user: str
    port: int
    authorized_keys_paths: tuple[str, ...]


@dataclass(frozen=True)
class Acceptance:
    physical_gates: tuple[str, ...]


@dataclass(frozen=True)
class Device:
    id: str
    name: str
    platform: str
    status: str
    detection: Detection
    storage: Storage
    ssh: SSH
    acceptance: Acceptance
    source: Path

    @classmethod
    def from_toml(cls, path: Path) -> "Device":
        with path.open("rb") as handle:
            data = tomllib.load(handle)

        try:
            detection_data = data["detection"]
            storage_data = data["storage"]
            ssh_data = data["ssh"]
            acceptance_data = data["acceptance"]
            device = cls(
                id=str(data["id"]),
                name=str(data["name"]),
                platform=str(data["platform"]),
                status=str(data["status"]),
                detection=Detection(
                    required_paths=tuple(map(str, detection_data["required_paths"])),
                    marker_file=str(detection_data["marker_file"]),
                    marker_tokens=tuple(map(str, detection_data["marker_tokens"])),
                ),
                storage=Storage(
                    books_root=str(storage_data["books_root"]),
                    koreader_root=str(storage_data["koreader_root"]),
                    installer_trigger=str(storage_data["installer_trigger"]),
                    recovery_marker=str(storage_data["recovery_marker"]),
                ),
                ssh=SSH(
                    user=str(ssh_data["user"]),
                    port=int(ssh_data["port"]),
                    authorized_keys_paths=tuple(
                        map(str, ssh_data["authorized_keys_paths"])
                    ),
                ),
                acceptance=Acceptance(
                    physical_gates=tuple(map(str, acceptance_data["physical_gates"])),
                ),
                source=path.resolve(),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise SafetyError(f"invalid device manifest {path}: {error}") from error

        device.validate()
        return device

    def validate(self) -> None:
        if not self.id or not self.name or not self.platform:
            raise SafetyError(
                f"device manifest has an empty identity field: {self.source}"
            )
        if not 1 <= self.ssh.port <= 65535:
            raise SafetyError(f"invalid SSH port for {self.id}: {self.ssh.port}")

        paths = [
            *self.detection.required_paths,
            self.detection.marker_file,
            self.storage.books_root,
            self.storage.koreader_root,
            self.storage.installer_trigger,
            self.storage.recovery_marker,
            *self.ssh.authorized_keys_paths,
        ]
        for value in filter(None, paths):
            relative_device_path(value)

    def matches(self, mount: Path) -> bool:
        if any(
            not under(mount, value).exists() for value in self.detection.required_paths
        ):
            return False
        if not self.detection.marker_file:
            return not self.detection.marker_tokens

        marker = under(mount, self.detection.marker_file)
        if not marker.is_file():
            return False
        marker_text = marker.read_text(encoding="utf-8", errors="replace")[:1_048_576]
        return all(token in marker_text for token in self.detection.marker_tokens)
