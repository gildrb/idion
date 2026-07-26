from pathlib import Path
import tempfile
import unittest

from koreader_appliance.registry import Registry
from koreader_appliance.safety import SafetyError


REPOSITORY = Path(__file__).resolve().parents[1]


class RegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = Registry(REPOSITORY / "adapters")

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

    def test_detects_each_kobo_adapter_without_cross_matching(self) -> None:
        markers = {
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
        self.assertEqual(set(markers), {device.id for device in self.registry.all() if device.platform == "kobo"})
        for expected, marker in markers.items():
            with self.subTest(device=expected):
                with tempfile.TemporaryDirectory() as temporary:
                    mount = Path(temporary)
                    (mount / ".kobo").mkdir()
                    (mount / ".kobo" / "version").write_text(
                        f"firmware,hardware,{marker}\n"
                    )
                    self.assertEqual(self.registry.detect(mount).id, expected)

    def test_detects_kindle_from_documents_and_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            mount = Path(temporary)
            (mount / "documents").mkdir()
            (mount / "system").mkdir()
            (mount / "system" / "version.txt").write_text("Kindle 5.16\n")
            self.assertEqual(self.registry.detect(mount).id, "kindle")

    def test_adapters_use_final_status_vocabulary(self) -> None:
        self.assertEqual(self.registry.get("kobo-clara-bw").status, "verified")
        self.assertEqual(self.registry.get("kobo-libra-2").status, "unverified")
        self.assertEqual(self.registry.get("kindle").status, "blocked")


if __name__ == "__main__":
    unittest.main()
