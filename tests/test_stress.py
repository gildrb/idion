from hashlib import sha256
import io
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
import zipfile

from koreader_appliance.cli import main
from koreader_appliance.manifest import ApplianceManifest
from koreader_appliance.registry import Registry
from koreader_appliance.safety import SafetyError
from koreader_appliance.state import plan


REPOSITORY = Path(__file__).resolve().parents[1]
MARKERS = {
    "kobo-clara-bw": "P365",
    "kobo-clara-hd": "N249",
    "kobo-clara-2e": "N506",
    "kobo-clara-colour": "N367",
    "kobo-libra-h2o": "N873",
    "kobo-libra-2": "N418",
    "kobo-libra-colour": "N428",
    "kobo-nia": "N306",
    "kobo-sage": "N778",
    "kobo-elipsa-2e": "N605",
    "kobo-forma": "N782",
}


class StressTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = Registry(REPOSITORY / "adapters")

    def _kobo_mount(self, root: Path, marker_text: str) -> Path:
        mount = root / "reader"
        (mount / ".kobo").mkdir(parents=True)
        (mount / ".kobo" / "version").write_text(marker_text, encoding="utf-8")
        return mount

    def test_every_kobo_adapter_detects_uniquely(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for device_id, marker in MARKERS.items():
                with self.subTest(device=device_id):
                    mount = self._kobo_mount(root / device_id, f"serial,{marker}\n")
                    self.assertEqual(self.registry.detect(mount).id, device_id)

    def test_mount_matching_two_adapters_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            mount = self._kobo_mount(
                Path(temporary), f"serial,{MARKERS['kobo-clara-hd']},{MARKERS['kobo-clara-2e']}\n"
            )
            with self.assertRaisesRegex(SafetyError, "exactly one device match"):
                self.registry.detect(mount)

    def test_corrupt_version_and_invalid_mounts_fail_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            corrupt = self._kobo_mount(root / "corrupt", b"\x00\xff\x80".decode("latin1"))
            (corrupt / ".kobo" / "version").write_bytes(b"\x00\xff\x80")
            with self.assertRaises(SafetyError):
                self.registry.detect(corrupt)

            empty = root / "empty"
            empty.mkdir()
            with self.assertRaises(SafetyError):
                self.registry.detect(empty)

            file_mount = root / "not-a-directory"
            file_mount.write_text("reader", encoding="utf-8")
            with self.assertRaises(SafetyError):
                self.registry.detect(file_mount)

            outer = self._kobo_mount(root / "outer", "serial,P365\n")
            inner = outer / "nested-reader"
            (inner / ".kobo").mkdir(parents=True)
            (inner / ".kobo" / "version").write_text("serial,N249\n", encoding="utf-8")
            self.assertEqual(self.registry.detect(outer).id, "kobo-clara-bw")

    def test_kindles_require_version_and_plan_without_install_step(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            mount = Path(temporary)
            (mount / "documents").mkdir()
            kindle = self.registry.get("kindle")
            with self.assertRaises(SafetyError):
                self.registry.detect(mount)

            manifest_path = mount.parent / "kindle.toml"
            manifest_path.write_text(
                'device = "kindle"\n'
                '[koreader]\narchive = "reader.zip"\nsha256 = "'
                + "0" * 64
                + '"\n[root_package]\npath = "root.tgz"\nsha256 = "'
                + "1" * 64
                + '"\n[backup]\nmanifest = "backup.json"\n',
                encoding="utf-8",
            )
            manifest = ApplianceManifest.from_toml(manifest_path)
            steps = plan(mount, manifest, kindle)
            self.assertTrue(steps)
            self.assertNotIn("installer-trigger", {step["action"] for step in steps})

    def test_setup_is_idempotent_for_three_models(self) -> None:
        for device_id in ("kobo-clara-bw", "kobo-libra-2", "kobo-forma"):
            with self.subTest(device=device_id), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                marker = MARKERS[device_id]
                mount = self._kobo_mount(root, f"serial,{marker}\n")
                archive = root / "reader.zip"
                with zipfile.ZipFile(archive, "w") as output:
                    output.writestr("koreader/reader.lua", "return true\n")
                    output.writestr("koreader/koreader.sh", "#!/bin/sh\n")
                package = root / "root.tgz"
                package.write_bytes(b"root-package-" + device_id.encode())
                manifest_path = root / "appliance.toml"
                manifest_path.write_text(
                    f'device = "{device_id}"\n'
                    '[koreader]\narchive = "reader.zip"\nsha256 = "'
                    + sha256(archive.read_bytes()).hexdigest()
                    + '"\n[root_package]\npath = "root.tgz"\nsha256 = "'
                    + sha256(package.read_bytes()).hexdigest()
                    + '"\n[backup]\nmanifest = "backups/backup-manifest.json"\n',
                    encoding="utf-8",
                )

                first_output = io.StringIO()
                with redirect_stdout(first_output):
                    self.assertEqual(
                        main(
                            [
                                "setup",
                                device_id,
                                str(mount),
                                "--manifest",
                                str(manifest_path),
                                "--yes",
                                "--allow-unverified",
                            ]
                        ),
                        0,
                    )
                first_state = {
                    path.relative_to(mount).as_posix(): path.read_bytes()
                    for path in mount.rglob("*")
                    if path.is_file()
                }

                second_output = io.StringIO()
                with redirect_stdout(second_output):
                    self.assertEqual(
                        main(
                            [
                                "setup",
                                device_id,
                                str(mount),
                                "--manifest",
                                str(manifest_path),
                                "--yes",
                                "--allow-unverified",
                            ]
                        ),
                        0,
                    )
                second_state = {
                    path.relative_to(mount).as_posix(): path.read_bytes()
                    for path in mount.rglob("*")
                    if path.is_file()
                }
                self.assertEqual(first_state, second_state)
                self.assertEqual(first_output.getvalue(), second_output.getvalue())

    def test_unknown_reader_refuses_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            mount = Path(temporary)
            (mount / "documents").mkdir()
            (mount / "vendor").write_text("unknown", encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["detect", str(mount)]), 1)
            self.assertNotIn("Traceback", output.getvalue())


if __name__ == "__main__":
    unittest.main()
