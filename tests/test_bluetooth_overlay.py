from pathlib import Path
import re
import unittest


REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = (
    REPOSITORY
    / "adapters/kobo-clara-bw/onboard/.adds/koreader/plugins/kobo_remote.koplugin"
)


class BluetoothOverlayTests(unittest.TestCase):
    def test_overlay_is_bluetooth_only_and_pinned_to_upstream(self) -> None:
        migration = (PLUGIN / "MIGRATION.md").read_text(encoding="utf-8")
        main = (PLUGIN / "main.lua").read_text(encoding="utf-8")
        self.assertIn("9ce2eb3d78771327aa2428251213a8b94d727209", migration)
        self.assertNotIn("virtual_library", main)
        self.assertNotIn("reading_state_sync", main)

    def test_suspend_dbus_calls_have_reply_deadlines(self) -> None:
        adapter = (
            PLUGIN / "src/lib/bluetooth/adapters/mtk_adapter.lua"
        ).read_text(encoding="utf-8")
        commands = re.findall(r'"(dbus-send[^"\\]*(?:\\.[^"\\]*)*)"', adapter)
        self.assertTrue(commands)
        self.assertTrue(
            all("--reply-timeout=" in command for command in commands), commands
        )

    def test_reconnect_does_not_wait_on_ui_thread(self) -> None:
        manager = (PLUGIN / "src/kobo_bluetooth.lua").read_text(encoding="utf-8")
        connection = manager.split("function KoboBluetooth:_handleConnection", 1)[1]
        connection = connection.split("\nend", 1)[0]
        self.assertIn("UIManager:scheduleIn", connection)
        self.assertNotIn("waitForBluetoothInputDevice", connection)
        self.assertNotIn("ffiUtil.sleep", connection)


if __name__ == "__main__":
    unittest.main()
