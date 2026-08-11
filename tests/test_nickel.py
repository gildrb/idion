from pathlib import Path
import tempfile
import unittest

from idion.nickel import (
    ANALYTICS_CONFIG,
    READER_CONFIG,
    apply_privacy,
    privacy_is_current,
)
from idion.registry import Registry
from idion.safety import SafetyError


REPOSITORY = Path(__file__).resolve().parents[1]


class NickelPrivacyTests(unittest.TestCase):
    def _mount(self, root: Path) -> tuple[Path, object]:
        mount = root / "reader"
        (mount / ".kobo").mkdir(parents=True)
        (mount / ".kobo/version").write_text("firmware,P365\n", encoding="utf-8")
        return mount, Registry(REPOSITORY / "adapters").get("kobo-clara-bw")

    def test_rewrites_only_target_values_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mount, device = self._mount(root)
            config = mount / READER_CONFIG
            analytics = mount / ANALYTICS_CONFIG
            config.parent.mkdir(parents=True, exist_ok=True)
            config.write_text(
                "[Other]\n"
                "unknown = preserve\n"
                "\n"
                "[ApplicationPreferences]\n"
                "AIRPLANE_MODE = false\n"
                "keep = exact\n"
                "SideloadedMode=false\n",
                encoding="utf-8",
            )
            analytics.write_text(
                "[Analytics]\nGAQueue = queued\nkeep = exact\n", encoding="utf-8"
            )

            apply_privacy(mount, device)
            first = (config.read_text(), analytics.read_text())
            self.assertIn("unknown = preserve\n", first[0])
            self.assertIn("keep = exact\n", first[0])
            self.assertIn("AIRPLANE_MODE = true\n", first[0])
            self.assertIn("SideloadedMode=true\n", first[0])
            self.assertIn("GAQueue = @Invalid()\n", first[1])
            self.assertTrue(privacy_is_current(mount, device))
            analytics.write_text(
                "[General]\nClientID=preserve\nGAQueue=fresh\n", encoding="utf-8"
            )
            self.assertTrue(privacy_is_current(mount, device))
            apply_privacy(mount, device)
            self.assertEqual(
                analytics.read_text(),
                "[General]\nClientID=preserve\nGAQueue=@Invalid()\n",
            )

    def test_absent_files_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            mount, device = self._mount(Path(temporary))
            apply_privacy(mount, device)
            self.assertEqual(
                (mount / READER_CONFIG).read_text(),
                "[ApplicationPreferences]\nAIRPLANE_MODE=true\nSideloadedMode=true\n",
            )
            self.assertFalse((mount / ANALYTICS_CONFIG).exists())

    def test_malformed_file_raises_safety_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mount, device = self._mount(root)
            config = mount / READER_CONFIG
            config.parent.mkdir(parents=True, exist_ok=True)
            config.write_text("not an ini line\n", encoding="utf-8")
            with self.assertRaises(SafetyError):
                apply_privacy(mount, device)
