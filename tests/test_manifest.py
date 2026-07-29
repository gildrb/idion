from hashlib import sha256
from contextlib import redirect_stdout
from dataclasses import replace
import io
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from koreader_appliance.backup import create_backup
from koreader_appliance.cli import main
from koreader_appliance.model import Device
from koreader_appliance.manifest import ApplianceManifest
from koreader_appliance.registry import Registry
from koreader_appliance.safety import SafetyError
from koreader_appliance.state import apply, plan, require_installable


REPOSITORY = Path(__file__).resolve().parents[1]


class ManifestTests(unittest.TestCase):
    def test_parses_relative_paths_and_defaults_library(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "appliance.toml"
            manifest_path.write_text(
                'device = "kobo-clara-bw"\n'
                "[koreader]\n"
                "archive = \"koreader.zip\"\n"
                f"sha256 = \"{'a' * 64}\"\n"
                "[root_package]\n"
                "path = \"KoboRoot.tgz\"\n"
                f"sha256 = \"{'b' * 64}\"\n"
                "[backup]\n"
                "manifest = \"backup/backup-manifest.json\"\n",
                encoding="utf-8",
            )
            manifest = ApplianceManifest.from_toml(manifest_path)
            self.assertEqual(manifest.koreader.path, (root / "koreader.zip").resolve())
            self.assertEqual(
                manifest.library.folders,
                ("Programming", "Linux", "Math", "Papers", "Manuals"),
            )

    def test_rejects_missing_required_pin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "appliance.toml"
            path.write_text(
                'device = "kobo-clara-bw"\n'
                "[koreader]\narchive = \"reader.zip\"\n"
                "[root_package]\npath = \"root.tgz\"\nsha256 = \""
                + "a" * 64
                + '\"\n[backup]\nmanifest = "backup.json"\n',
                encoding="utf-8",
            )
            with self.assertRaises(SafetyError):
                ApplianceManifest.from_toml(path)

    def test_hash_pin_refuses_changed_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "reader.zip"
            archive.write_bytes(b"not-the-pinned-archive")
            package = root / "root.tgz"
            package.write_bytes(b"root")
            backup = root / "backup.json"
            backup.write_text("{}")
            manifest_path = root / "appliance.toml"
            manifest_path.write_text(
                'device = "kobo-clara-bw"\n'
                "[koreader]\narchive = \"reader.zip\"\nsha256 = \""
                + "0" * 64
                + '\"\n[root_package]\npath = "root.tgz"\nsha256 = "'
                + sha256(package.read_bytes()).hexdigest()
                + '"\n[backup]\nmanifest = "backup.json"\n',
                encoding="utf-8",
            )
            manifest = ApplianceManifest.from_toml(manifest_path)
            with self.assertRaises(SafetyError):
                from koreader_appliance.state import _verify_pin

                _verify_pin(manifest.koreader.path, manifest.koreader.sha256, "archive")

    def _fixture(self) -> tuple[Path, ApplianceManifest, object]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        mount = root / "reader"
        (mount / ".kobo").mkdir(parents=True)
        (mount / ".kobo" / "version").write_text("P365\n")
        backup_destination = root / "backup"
        device = Registry(REPOSITORY / "adapters").detect(mount)
        create_backup(mount, backup_destination, device)

        archive = root / "reader.zip"
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("koreader/reader.lua", "return true\n")
            output.writestr("koreader/koreader.sh", "#!/bin/sh\n")
        package = root / "root.tgz"
        package.write_bytes(b"root-package")
        settings = root / "settings.lua"
        settings.write_text("return {}\n")
        manifest_path = root / "appliance.toml"
        manifest_path.write_text(
            'device = "kobo-clara-bw"\n'
            "[koreader]\narchive = \"reader.zip\"\nsha256 = \""
            + sha256(archive.read_bytes()).hexdigest()
            + '"\n[root_package]\npath = "root.tgz"\nsha256 = "'
            + sha256(package.read_bytes()).hexdigest()
            + '"\n[backup]\nmanifest = "backup/backup-manifest.json"\n'
            '[settings]\nprofile = "settings.lua"\n'
            '[library]\nfolders = ["Books", "Manuals"]\n',
            encoding="utf-8",
        )
        return temporary, ApplianceManifest.from_toml(manifest_path), device

    def test_empty_detected_mount_is_all_pending_then_apply_is_idempotent(self) -> None:
        temporary, manifest, device = self._fixture()
        try:
            mount = Path(temporary.name) / "reader"
            before = plan(mount, manifest, device)
            self.assertTrue(before)
            self.assertTrue(all(step["status"] == "pending" for step in before))
            self.assertTrue(all(step["status"] == "ok" for step in apply(mount, manifest, device)))
            self.assertTrue(all(step["status"] == "ok" for step in apply(mount, manifest, device)))
        finally:
            temporary.cleanup()

    def test_parses_nickelmenu_launch_and_ssh_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "appliance.toml"
            manifest_path.write_text(
                'device = "kobo-clara-bw"\n'
                '[koreader]\narchive = "reader.zip"\nsha256 = "'
                + "a" * 64
                + '"\n[root_package]\npath = "root.tgz"\nsha256 = "'
                + "b" * 64
                + '"\n[backup]\nmanifest = "backup.json"\n'
                '[launch]\nmode = "nickelmenu"\n'
                '[ssh]\nauthorized_key = "reader.pub"\n',
                encoding="utf-8",
            )

            manifest = ApplianceManifest.from_toml(manifest_path)

            self.assertEqual(manifest.launch.mode, "nickelmenu")
            self.assertEqual(
                manifest.ssh.authorized_key, (root / "reader.pub").resolve()
            )

    def test_setup_creates_declared_backup_before_apply(self) -> None:
        temporary, manifest, device = self._fixture()
        try:
            root = Path(temporary.name)
            mount = root / "reader"
            manifest_path = manifest.source
            shutil.rmtree(root / "backup")
            output = io.StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "setup",
                        device.id,
                        str(mount),
                        "--manifest",
                        str(manifest_path),
                        "--yes",
                    ]
                )
            self.assertEqual(result, 0)
            self.assertTrue((root / "backup" / "backup-manifest.json").is_file())
        finally:
            temporary.cleanup()

    def test_unverified_gate_requires_explicit_override(self) -> None:
        temporary, manifest, device = self._fixture()
        try:
            unverified = Device(
                id=device.id,
                name=device.name,
                platform=device.platform,
                status="unverified",
                detection=device.detection,
                storage=device.storage,
                ssh=device.ssh,
                acceptance=device.acceptance,
                source=device.source,
            )
            mount = Path(temporary.name) / "reader"
            with self.assertRaisesRegex(SafetyError, "not verified on hardware"):
                apply(mount, manifest, unverified)
            result = apply(mount, manifest, unverified, allow_unverified=True)
            self.assertTrue(all(step["status"] == "ok" for step in result))
        finally:
            temporary.cleanup()

    def test_verified_status_does_not_require_override(self) -> None:
        temporary, manifest, device = self._fixture()
        try:
            trusted = replace(device, status="verified")
            result = apply(Path(temporary.name) / "reader", manifest, trusted)
            self.assertTrue(all(step["status"] == "ok" for step in result))
        finally:
            temporary.cleanup()

    def test_blocked_kobo_is_refused_even_with_override(self) -> None:
        device = Registry(REPOSITORY / "adapters").get("kobo-clara-bw")
        blocked = replace(device, status="blocked")
        with self.assertRaisesRegex(SafetyError, "blocked"):
            require_installable(blocked, allow_unverified=True)

    def test_unknown_status_requires_override(self) -> None:
        device = Registry(REPOSITORY / "adapters").get("kobo-clara-bw")
        unknown = replace(device, status="future-status")
        with self.assertRaisesRegex(SafetyError, "not verified"):
            require_installable(unknown)

    def test_apply_refuses_kindle_vendor_boot_chain(self) -> None:
        temporary, manifest, _ = self._fixture()
        try:
            kindle = Registry(REPOSITORY / "adapters").get("kindle")
            with self.assertRaisesRegex(SafetyError, "KUAL/MRPI"):
                apply(Path(temporary.name) / "reader", manifest, kindle)
        finally:
            temporary.cleanup()
