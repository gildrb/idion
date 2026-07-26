from pathlib import Path
import tempfile
import unittest

from koreader_appliance.profiles import apply_manga_profile
from koreader_appliance.safety import SafetyError


class MangaProfileTests(unittest.TestCase):
    def test_converts_tiled_pdf_to_one_complete_page_per_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            sidecar = Path(temporary) / "metadata.pdf.lua"
            sidecar.write_text(
                """return {
    ["kopt_max_columns"] = 2,
    ["kopt_page_scroll"] = 0,
    ["kopt_trim_page"] = 3,
    ["kopt_zoom_mode_genus"] = 2,
    ["kopt_zoom_mode_type"] = 2,
    ["normal_zoom_mode"] = "columns",
    ["zoom_mode"] = "columns",
}
"""
            )
            backup = apply_manga_profile(sidecar)
            updated = sidecar.read_text()

            self.assertTrue(backup.is_file())
            self.assertIn('["zoom_mode"] = "page",', updated)
            self.assertIn('["normal_zoom_mode"] = "page",', updated)
            self.assertIn('["kopt_max_columns"] = 1,', updated)
            self.assertIn('["kopt_trim_page"] = 0,', updated)

    def test_requires_an_exact_pdf_sidecar_name(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            wrong = Path(temporary) / "settings.reader.lua"
            wrong.write_text("return {}\n")
            with self.assertRaises(SafetyError):
                apply_manga_profile(wrong)


if __name__ == "__main__":
    unittest.main()
