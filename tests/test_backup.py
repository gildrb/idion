import json
from pathlib import Path
import tempfile
import unittest

from idion.backup import create_backup
from idion.registry import Registry
from idion.safety import SafetyError


REPOSITORY = Path(__file__).resolve().parents[1]


class BackupTests(unittest.TestCase):
    def test_backup_hashes_content_and_excludes_macos_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mount = root / "reader"
            mount.mkdir()
            (mount / ".kobo").mkdir()
            (mount / ".kobo" / "version").write_text("P365\n")
            (mount / "Books").mkdir()
            (mount / "Books" / "example.epub").write_bytes(b"book-content")
            (mount / ".Spotlight-V100").mkdir()
            (mount / ".Spotlight-V100" / "index").write_bytes(b"transient")

            device = Registry(REPOSITORY / "adapters").detect(mount)
            destination = root / "backup"
            manifest = create_backup(mount, destination, device)

            self.assertEqual(manifest["file_count"], 2)
            self.assertEqual(
                (destination / "Books" / "example.epub").read_bytes(), b"book-content"
            )
            self.assertFalse((destination / ".Spotlight-V100").exists())
            stored = json.loads((destination / "backup-manifest.json").read_text())
            self.assertEqual(stored["device"]["id"], "kobo-clara-bw")

    def test_backup_destination_cannot_be_inside_reader(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            mount = Path(temporary)
            (mount / ".kobo").mkdir()
            (mount / ".kobo" / "version").write_text("P365\n")
            device = Registry(REPOSITORY / "adapters").detect(mount)
            with self.assertRaises(SafetyError):
                create_backup(mount, mount / "backup", device)


if __name__ == "__main__":
    unittest.main()
