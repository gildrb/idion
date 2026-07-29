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

    def test_nickelmenu_mode_is_transactional_and_preserves_user_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mount = root / "reader"
            (mount / ".kobo").mkdir(parents=True)
            (mount / ".kobo" / "version").write_text("P365\n")
            archive = root / "koreader.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("koreader/reader.lua", "return true\n")
                output.writestr("koreader/koreader.sh", "#!/bin/sh\n")
            package = root / "KoboRoot.tgz"
            package.write_bytes(b"nickelmenu")
            profile = root / "base.lua"
            profile.write_text("return { first = true }\n")
            key = root / "reader.pub"
            key.write_text("ssh-ed25519 AAAATEST reader\n")
            device = Registry(REPOSITORY / "adapters").detect(mount)

            first = stage_koreader(
                mount,
                archive,
                package,
                device,
                profile,
                launch_mode="nickelmenu",
                authorized_key=key,
            )
            settings = mount / ".adds/koreader/settings.reader.lua"
            settings.write_text("return { user = true }\n")
            second = stage_koreader(
                mount,
                archive,
                package,
                device,
                profile,
                launch_mode="nickelmenu",
                authorized_key=key,
            )

            self.assertEqual(first["redeployed"], "true")
            self.assertEqual(second["redeployed"], "false")
            self.assertEqual(settings.read_text(), "return { user = true }\n")
            self.assertFalse((mount / ".kobo/ssh-enabled").exists())
            self.assertTrue((mount / ".adds/nm/koreader").is_file())
            self.assertIn(
                "exec /bin/sh /mnt/onboard/.adds/nm/koreader-launch.sh",
                (mount / ".adds/nm/koreader").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "/mnt/onboard/.adds/koreader.previous",
                (mount / ".adds/nm/koreader-launch.sh").read_text(
                    encoding="utf-8"
                ),
            )
            self.assertEqual(
                (mount / ".adds/koreader/settings/SSH/authorized_keys").read_text(),
                "ssh-ed25519 AAAATEST reader\n",
            )
            self.assertTrue(
                (
                    mount
                    / ".adds/koreader/plugins/kobo_remote.koplugin/main.lua"
                ).is_file()
            )


if __name__ == "__main__":
    unittest.main()
