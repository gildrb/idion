from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from koreader_appliance.cli import _find_mount
from koreader_appliance import cli
from koreader_appliance.registry import Registry


REPOSITORY = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def test_find_mount_accepts_candidate_that_is_the_reader(self) -> None:
        registry = Registry(REPOSITORY / "adapters")
        device = registry.get("kobo-clara-bw")
        with tempfile.TemporaryDirectory() as temporary:
            mount = Path(temporary)
            (mount / ".kobo").mkdir()
            (mount / ".kobo" / "version").write_text("firmware,P365\n")
            self.assertEqual(_find_mount(registry, device, [mount]), mount)

    def test_staging_beta_uses_shared_default_profile(self) -> None:
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
                    "allow_untested": True,
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


if __name__ == "__main__":
    unittest.main()
