from pathlib import Path
import tempfile
import unittest

from koreader_appliance.registry import Registry
from koreader_appliance.safety import SafetyError


REPOSITORY = Path(__file__).resolve().parents[1]


class RegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = Registry(REPOSITORY / "devices")

    def test_detects_clara_bw_by_storage_and_product_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            mount = Path(temporary)
            (mount / ".kobo").mkdir()
            (mount / ".kobo" / "version").write_text("firmware,P365\n")
            device = self.registry.detect(mount)
            self.assertEqual(device.id, "kobo-clara-bw")

    def test_rejects_volume_label_without_product_marker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="KOBOeReader-") as temporary:
            mount = Path(temporary)
            (mount / ".kobo").mkdir()
            (mount / ".kobo" / "version").write_text("unknown-device\n")
            with self.assertRaises(SafetyError):
                self.registry.detect(mount)


if __name__ == "__main__":
    unittest.main()
