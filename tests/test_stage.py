import io
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile

from koreader_appliance.registry import Registry
from koreader_appliance.safety import SafetyError
from koreader_appliance.stage import (
    SYNCTHING_IGNORE,
    library_tree_hash,
    stage_koreader,
)


REPOSITORY = Path(__file__).resolve().parents[1]


class StageTests(unittest.TestCase):
    def test_installs_pinned_reading_streak_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mount = root / "reader"
            (mount / ".kobo").mkdir(parents=True)
            (mount / ".kobo/version").write_text("P365\n")
            archive = root / "koreader.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("koreader/reader.lua", "return true\n")
                output.writestr("koreader/koreader.sh", "#!/bin/sh\n")
            plugin = root / "readingstreak.zip"
            with zipfile.ZipFile(plugin, "w") as output:
                output.writestr(
                    "readingstreak.koplugin-1.3.6/main.lua", "return true\n"
                )
            package = root / "KoboRoot.tgz"
            package.write_bytes(b"nickelmenu")
            device = Registry(REPOSITORY / "adapters").detect(mount)

            stage_koreader(
                mount,
                archive,
                package,
                device,
                launch_mode="nickelmenu",
                reading_streak_plugin=plugin,
            )

            installed = mount / ".adds/koreader/plugins/readingstreak.koplugin/main.lua"
            self.assertEqual(installed.read_text(), "return true\n")

    def test_restores_state_without_stale_cache_or_backup_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mount = root / "reader"
            (mount / ".kobo").mkdir(parents=True)
            (mount / ".kobo/version").write_text("P365\n")
            archive = root / "koreader.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("koreader/reader.lua", "return true\n")
                output.writestr("koreader/koreader.sh", "#!/bin/sh\n")
            package = root / "KoboRoot.tgz"
            package.write_bytes(b"nickelmenu")
            state = root / "backup/.adds/koreader"
            (state / "settings").mkdir(parents=True)
            (state / "settings/statistics.sqlite3").write_bytes(b"statistics")
            (state / "docsettings").mkdir()
            (state / "docsettings/book.lua").write_text("return {}\n")
            (state / "cache").mkdir()
            (state / "cache/stale").write_text("discard me\n")
            (state / "patches").mkdir()
            (state / "patches/old-policy.lua").write_text("error('stale')\n")
            device = Registry(REPOSITORY / "adapters").detect(mount)

            stage_koreader(
                mount,
                archive,
                package,
                device,
                launch_mode="nickelmenu",
                state_source=state,
                state_backup_sha256="a" * 64,
            )

            installed = mount / ".adds/koreader"
            self.assertEqual(
                (installed / "settings/statistics.sqlite3").read_bytes(),
                b"statistics",
            )
            self.assertTrue((installed / "docsettings/book.lua").is_file())
            self.assertFalse((installed / "cache/stale").exists())
            self.assertFalse((installed / "patches/old-policy.lua").exists())
            self.assertTrue((installed / "patches/2-appliance-policy.lua").is_file())

    def test_installs_pinned_syncthing_plugin_and_binary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mount = root / "reader"
            (mount / ".kobo").mkdir(parents=True)
            (mount / ".kobo/version").write_text("P365\n")
            archive = root / "koreader.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("koreader/reader.lua", "return true\n")
                output.writestr("koreader/koreader.sh", "#!/bin/sh\n")
            plugin = root / "kosyncthing_plus.koplugin.zip"
            with zipfile.ZipFile(plugin, "w") as output:
                output.writestr(
                    "kosyncthing_plus.koplugin/main.lua", "return true\n"
                )
            binary = root / "syncthing-linux-arm.tar.gz"
            with tarfile.open(binary, "w:gz") as output:
                content = b"syncthing"
                member = tarfile.TarInfo("syncthing-linux-arm/syncthing")
                member.size = len(content)
                output.addfile(member, io.BytesIO(content))
            package = root / "KoboRoot.tgz"
            package.write_bytes(b"nickelmenu")
            device = Registry(REPOSITORY / "adapters").detect(mount)

            stage_koreader(
                mount,
                archive,
                package,
                device,
                launch_mode="nickelmenu",
                syncthing_plugin=plugin,
                syncthing_binary=binary,
            )

            installed = (
                mount
                / ".adds/koreader/plugins/kosyncthing_plus.koplugin/syncthing"
            )
            self.assertEqual(installed.read_bytes(), b"syncthing")
            self.assertTrue(installed.stat().st_mode & 0o100)
            self.assertEqual((mount / ".stignore").read_text(), SYNCTHING_IGNORE)

    def test_stages_additively_and_enables_key_only_ssh_boot_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mount = root / "reader"
            (mount / ".kobo").mkdir(parents=True)
            (mount / ".kobo" / "version").write_text("P365\n")
            (mount / "._reader").write_bytes(b"metadata")
            (mount / ".kobo/._version").write_bytes(b"metadata")
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
            self.assertFalse((mount / "._reader").exists())
            self.assertFalse((mount / ".kobo/._version").exists())
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
            key.write_text(
                "ssh-ed25519 AAAATEST reader\n"
                "ssh-ed25519 AAAASERVER backup-server\n"
            )
            library = root / "library"
            (library / "Author").mkdir(parents=True)
            (library / "Author/book.epub").write_bytes(b"book")
            (library / "Author/._book.epub").write_bytes(b"metadata")
            library_hash, _ = library_tree_hash(library)
            device = Registry(REPOSITORY / "adapters").detect(mount)

            first = stage_koreader(
                mount,
                archive,
                package,
                device,
                profile,
                launch_mode="nickelmenu",
                authorized_key=key,
                library_source=library,
                library_sha256=library_hash,
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
                library_source=library,
                library_sha256=library_hash,
            )

            self.assertEqual(first["redeployed"], "true")
            self.assertEqual(second["redeployed"], "false")
            self.assertEqual(settings.read_text(), "return { user = true }\n")
            self.assertFalse((mount / ".kobo/ssh-enabled").exists())
            self.assertTrue((mount / ".adds/nm/koreader").is_file())
            self.assertIn(
                "exec /bin/sh /mnt/onboard/.adds/koreader-appliance/koreader-launch.sh",
                (mount / ".adds/nm/koreader").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "/mnt/onboard/.adds/koreader.previous",
                (mount / ".adds/koreader-appliance/koreader-launch.sh").read_text(
                    encoding="utf-8"
                ),
            )
            self.assertIn(
                "/sbin/reboot",
                (mount / ".adds/koreader-appliance/koreader-launch.sh").read_text(
                    encoding="utf-8"
                ),
            )
            self.assertFalse((mount / ".adds/nm/koreader-launch.sh").exists())
            self.assertTrue((mount / "Books/Author/book.epub").is_file())
            self.assertFalse((mount / "Books/Author/._book.epub").exists())
            self.assertIn(
                "ExcludeSyncFolders=(\\.(?!kobo|adobe).+|([^.][^/]*/)+\\..+)",
                (mount / ".kobo/Kobo/Kobo eReader.conf").read_text(),
            )
            self.assertNotIn(
                r"ExcludeSyncFolders=(\\.",
                (mount / ".kobo/Kobo/Kobo eReader.conf").read_text(),
            )
            self.assertIn(
                "SideloadedMode=true",
                (mount / ".kobo/Kobo/Kobo eReader.conf").read_text(),
            )
            self.assertEqual(
                (mount / ".adds/koreader/settings/SSH/authorized_keys").read_text(),
                "ssh-ed25519 AAAATEST reader\n"
                "ssh-ed25519 AAAASERVER backup-server\n",
            )
            self.assertTrue(
                (
                    mount
                    / ".adds/koreader/plugins/kobo_remote.koplugin/main.lua"
                ).is_file()
            )


if __name__ == "__main__":
    unittest.main()
