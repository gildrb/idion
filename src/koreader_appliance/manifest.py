from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import tomllib

from .safety import SafetyError


DEFAULT_LIBRARY_FOLDERS = ("Programming", "Linux", "Math", "Papers", "Manuals")
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(frozen=True)
class PinnedFile:
    path: Path
    sha256: str


@dataclass(frozen=True)
class KoreaderConfig(PinnedFile):
    pass


@dataclass(frozen=True)
class RootPackageConfig(PinnedFile):
    pass


@dataclass(frozen=True)
class BackupConfig:
    manifest: Path


@dataclass(frozen=True)
class SettingsConfig:
    profile: Path


@dataclass(frozen=True)
class LibraryConfig:
    folders: tuple[str, ...]


@dataclass(frozen=True)
class ApplianceManifest:
    device: str
    koreader: KoreaderConfig
    root_package: RootPackageConfig
    backup: BackupConfig
    settings: SettingsConfig | None
    library: LibraryConfig
    source: Path

    @classmethod
    def from_toml(cls, path: Path) -> "ApplianceManifest":
        source = path.expanduser().resolve()
        try:
            with source.open("rb") as handle:
                data = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as error:
            raise SafetyError(
                f"could not read appliance manifest {source}: {error}"
            ) from error

        try:
            cls._table(
                data,
                {"device", "koreader", "root_package", "backup", "settings", "library"},
            )
            koreader_data = data["koreader"]
            root_data = data["root_package"]
            backup_data = data["backup"]
            settings_data = data.get("settings")
            library_data = data.get("library", {})
            cls._table(koreader_data, {"archive", "sha256"}, "koreader")
            cls._table(root_data, {"path", "sha256"}, "root_package")
            cls._table(backup_data, {"manifest"}, "backup")
            if settings_data is not None:
                cls._table(settings_data, {"profile"}, "settings")
            cls._table(library_data, {"folders"}, "library")
            koreader = KoreaderConfig(
                path=cls._path(source, koreader_data["archive"], "koreader.archive"),
                sha256=cls._hash(koreader_data["sha256"], "koreader.sha256"),
            )
            root_package = RootPackageConfig(
                path=cls._path(source, root_data["path"], "root_package.path"),
                sha256=cls._hash(root_data["sha256"], "root_package.sha256"),
            )
            settings = (
                SettingsConfig(
                    profile=cls._path(
                        source, settings_data["profile"], "settings.profile"
                    )
                )
                if settings_data is not None
                else None
            )
            library = LibraryConfig(
                folders=cls._folders(library_data.get("folders", DEFAULT_LIBRARY_FOLDERS))
            )
            manifest = cls(
                device=cls._string(data["device"], "device"),
                koreader=koreader,
                root_package=root_package,
                backup=BackupConfig(
                    manifest=cls._path(
                        source, backup_data["manifest"], "backup.manifest"
                    )
                ),
                settings=settings,
                library=library,
                source=source,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise SafetyError(
                f"invalid appliance manifest {source}: {error}"
            ) from error
        manifest.validate()
        return manifest

    @staticmethod
    def _table(
        value: object, allowed: set[str], name: str = "top-level"
    ) -> None:
        if not isinstance(value, dict):
            raise SafetyError(f"{name} must be a TOML table")
        unknown = set(value) - allowed
        if unknown:
            raise SafetyError(
                f"{name} contains unsupported fields: {', '.join(sorted(unknown))}"
            )

    @staticmethod
    def _string(value: object, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise SafetyError(f"{field} must be a non-empty string")
        return value

    @staticmethod
    def _path(source: Path, value: object, field: str) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise SafetyError(f"{field} must be a path")
        path = Path(value).expanduser()
        return (
            (source.parent / path).resolve()
            if not path.is_absolute()
            else path.resolve()
        )

    @staticmethod
    def _hash(value: object, field: str) -> str:
        if not isinstance(value, str) or not _SHA256.fullmatch(value):
            raise SafetyError(f"{field} must be a 64-character SHA-256 hex digest")
        return value.lower()

    @staticmethod
    def _folders(value: object) -> tuple[str, ...]:
        if not isinstance(value, (list, tuple)) or any(
            not isinstance(folder, str) or not folder.strip() for folder in value
        ):
            raise SafetyError("library.folders must be a list of non-empty paths")
        folders = tuple(value)
        if len(set(folders)) != len(folders):
            raise SafetyError("library.folders must not contain duplicates")
        if any(
            Path(folder).is_absolute() or ".." in Path(folder).parts
            for folder in folders
        ):
            raise SafetyError("library.folders must contain relative paths")
        return folders

    def validate(self) -> None:
        if not self.device:
            raise SafetyError("appliance manifest device is empty")
        if not self.library.folders:
            raise SafetyError("library.folders must not be empty")

    @staticmethod
    def hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
