from pathlib import Path
import tempfile
import unittest

from koreader_appliance.cli import _find_mount
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


if __name__ == "__main__":
    unittest.main()
