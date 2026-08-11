from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import tempfile
import tarfile
import unittest
from unittest.mock import patch
import zipfile

from koreader_appliance.cli import _find_mount
from koreader_appliance import cli
from koreader_appliance.backup import verify_backup_manifest
from koreader_appliance.registry import Registry
from koreader_appliance.safety import SafetyError
from koreader_appliance.validate import validate_live
from koreader_appliance.manifest import ApplianceManifest


REPOSITORY = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def test_version_reports_package_version(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            with self.assertRaises(SystemExit) as result:
                cli.main(["--version"])
        self.assertEqual(result.exception.code, 0)
        self.assertRegex(output.getvalue(), r"koreader-appliance 1\.0\.0\n")

    def test_unknown_shorthand_device_has_repo_error_format(self) -> None:
        error = io.StringIO()
        with redirect_stderr(error):
            result = cli.main(["not-a-device"])
        self.assertEqual(result, 1)
        self.assertEqual(error.getvalue(), "error: unknown device adapter: not-a-device\n")

    def test_find_mount_accepts_candidate_that_is_the_reader(self) -> None:
        registry = Registry(REPOSITORY / "adapters")
        device = registry.get("kobo-clara-bw")
        with tempfile.TemporaryDirectory() as temporary:
            mount = Path(temporary)
            (mount / ".kobo").mkdir()
            (mount / ".kobo" / "version").write_text("firmware,P365\n")
            self.assertEqual(_find_mount(registry, device, [mount]), mount)

    def test_unverified_device_uses_shared_default_profile(self) -> None:
        registry = Registry(REPOSITORY / "adapters")
        device = registry.get("kobo-libra-2")
        with tempfile.TemporaryDirectory() as temporary:
            mount = Path(temporary)
            arguments = type(
                "Arguments",
                (),
                {
                    "device": device.id,
                    "device_dir": REPOSITORY / "adapters",
                    "mount": mount,
                    "koreader": mount / "reader.zip",
                    "root_package": mount / "root.tgz",
                    "backup_manifest": mount / "backup.json",
                    "settings": None,
                    "allow_unverified": True,
                    "launch_mode": "autostart",
                    "authorized_key": None,
                },
            )()
            with (
                patch.object(cli, "require_installable"),
                patch.object(cli, "verify_backup_manifest"),
                patch.object(cli, "stage_koreader", return_value={}) as stage,
            ):
                cli.stage_command(arguments)
            self.assertEqual(
                stage.call_args.args[-1],
                REPOSITORY / "adapters" / "_kobo-common" / "profiles" / "base.lua",
            )

    def test_malformed_backup_manifest_is_a_safety_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mount = root / "mount"
            mount.mkdir()
            manifest = root / "backup" / "backup-manifest.json"
            manifest.parent.mkdir()
            manifest.write_text("{", encoding="utf-8")
            device = Registry(REPOSITORY / "adapters").get("kobo-clara-bw")
            with self.assertRaises(SafetyError):
                verify_backup_manifest(manifest, device, mount)

    def test_malformed_build_manifest_is_a_safety_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "build.json"
            manifest.write_text("{", encoding="utf-8")
            with self.assertRaises(SafetyError):
                validate_live("clara", manifest, root / "evidence")

    def test_setup_generates_manifest_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mount = root / "reader"
            (mount / ".kobo").mkdir(parents=True)
            (mount / ".kobo/version").write_text("firmware,P365\n", encoding="utf-8")

            koreader_root = root / "koreader"
            (koreader_root / ".adds/koreader").mkdir(parents=True)
            (koreader_root / ".adds/koreader/reader.lua").write_text(
                "return {}\n", encoding="utf-8"
            )
            (koreader_root / ".adds/koreader/koreader.sh").write_text(
                "#!/bin/sh\n", encoding="utf-8"
            )
            koreader = root / "koreader.zip"
            with zipfile.ZipFile(koreader, "w") as archive:
                archive.write(
                    koreader_root / ".adds/koreader/reader.lua",
                    ".adds/koreader/reader.lua",
                )
                archive.write(
                    koreader_root / ".adds/koreader/koreader.sh",
                    ".adds/koreader/koreader.sh",
                )

            nickel_root = root / "nickel"
            (nickel_root / "usr/local/Kobo/imageformats").mkdir(parents=True)
            (nickel_root / "usr/local/Kobo/imageformats/libnm.so").write_bytes(b"nm")
            nickel = root / "NickelMenu-KoboRoot.tgz"
            with tarfile.open(nickel, "w:gz") as archive:
                archive.add(nickel_root / "usr", "usr")

            home = root / "home"
            home.mkdir()
            arguments = [
                "setup",
                "kobo-clara-bw",
                str(mount),
                "--koreader",
                str(koreader),
                "--nickelmenu-package",
                str(nickel),
                "--launch-mode",
                "nickelmenu",
                "--yes",
            ]
            with patch.dict("os.environ", {"HOME": str(home)}, clear=False):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    self.assertEqual(cli.main(arguments), 0)
                (mount / ".kobo/Kobo/Analytics.conf").write_text(
                    "[General]\nClientID=preserve\nGAQueue=fresh\n",
                    encoding="utf-8",
                )
                second_output = io.StringIO()
                with redirect_stdout(second_output), redirect_stderr(io.StringIO()):
                    self.assertEqual(cli.main(arguments), 0)
                second_result = json.loads(second_output.getvalue())
                self.assertTrue(second_result["state"])
                self.assertTrue(
                    all(step["status"] == "ok" for step in second_result["state"])
                )
                self.assertEqual(
                    next(
                        step["status"]
                        for step in second_result["state"]
                        if step["action"] == "nickel-privacy"
                    ),
                    "ok",
                )
                output = io.StringIO()
                error = io.StringIO()
                with redirect_stdout(output), redirect_stderr(error):
                    self.assertEqual(
                        cli.main(
                            [
                                "setup",
                                "kobo-clara-bw",
                                str(mount),
                                "--launch-mode",
                                "nickelmenu",
                                "--yes",
                            ]
                        ),
                        0,
                    )
                self.assertEqual(error.getvalue(), "")
                self.assertEqual(
                    ApplianceManifest.from_toml(
                        home
                        / ".config/koreader-appliance/kobo-clara-bw.toml"
                    ).launch.mode,
                    "nickelmenu",
                )

            manifest_path = (
                home
                / ".config/koreader-appliance/kobo-clara-bw.toml"
            )
            manifest = ApplianceManifest.from_toml(manifest_path)
            self.assertEqual(manifest.device, "kobo-clara-bw")
            self.assertEqual(manifest.library.folders, ())
            self.assertTrue(
                all(
                    not (mount / "mnt/onboard" / folder).exists()
                    for folder in ("Programming", "Linux", "Math", "Papers", "Manuals")
                )
            )


if __name__ == "__main__":
    unittest.main()
