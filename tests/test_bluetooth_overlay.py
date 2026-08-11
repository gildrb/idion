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

    def test_appliance_policy_disables_every_plugin_defensively(self) -> None:
        patches = PLUGIN.parents[1] / "patches"
        policy = (patches / "2-appliance-policy.lua").read_text(encoding="utf-8")
        cleanup = (patches / "9-appliance-stop-ssh.lua").read_text(encoding="utf-8")

        self.assertIn('local data_storage = require("datastorage")', policy)
        self.assertIn('lfs.currentdir() .. "/plugins"', policy)
        self.assertIn('data_storage:getDataDir() .. "/plugins"', policy)
        self.assertIn('readSetting("extra_plugin_paths")', policy)
        self.assertIn("for entry in lfs.dir(path) do", policy)
        self.assertNotIn("DataStorage:", policy)
        self.assertIn('disabled[entry:sub(1, -10)] = true', policy)
        self.assertIn("disable_known_plugins()", policy)
        self.assertIn('G_reader_settings:saveSetting("SSH_key_only_auth", true)', policy)
        self.assertIn('G_reader_settings:saveSetting("SSH_autostart", false)', policy)
        self.assertNotIn('saveSetting("syncthing_', policy)
        self.assertIn('"statistics",', policy)
        self.assertIn('"kobo_remote",', policy)
        self.assertIn('"readingstreak",', policy)
        self.assertIn("dropbear_koreader.pid", cleanup)


if __name__ == "__main__":
    unittest.main()
