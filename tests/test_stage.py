from pathlib import Path
import tempfile
import unittest
import zipfile

from koreader_appliance.registry import Registry
from koreader_appliance.safety import SafetyError
from koreader_appliance.stage import stage_koreader


REPOSITORY = Path(__file__).resolve().parents[1]


class StageTests(unittest.TestCase):
    def test_stages_additively_and_enables_key_only_ssh_boot_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mount = root / "reader"
            (mount / ".kobo").mkdir(parents=True)
            (mount / ".kobo" / "version").write_text("P365\n")
            archive = root / "koreader.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("koreader/reader.lua", "return true\n")
                output.writestr("koreader/koreader.sh", "#!/bin/sh\n")
            root_package = root / "KoboRoot.tgz"
            root_package.write_bytes(b"root-package")
            device = Registry(REPOSITORY / "adapters").detect(mount)

            result = stage_koreader(mount, archive, root_package, device)

            self.assertTrue((mount / ".adds" / "koreader" / "reader.lua").is_file())
            self.assertEqual(
                (mount / ".kobo" / "KoboRoot.tgz").read_bytes(), b"root-package"
            )
            self.assertTrue((mount / ".kobo" / "ssh-enabled").is_file())
            self.assertEqual(len(result["installer_sha256"]), 64)

    def test_rejects_zip_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mount = root / "reader"
            (mount / ".kobo").mkdir(parents=True)
            (mount / ".kobo" / "version").write_text("P365\n")
            archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("../escape", "bad")
            root_package = root / "KoboRoot.tgz"
            root_package.write_bytes(b"root-package")
            device = Registry(REPOSITORY / "adapters").detect(mount)
            with self.assertRaises(SafetyError):
                stage_koreader(mount, archive, root_package, device)


if __name__ == "__main__":
    unittest.main()
