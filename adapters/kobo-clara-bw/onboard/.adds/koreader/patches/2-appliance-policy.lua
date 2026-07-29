local disabled = G_reader_settings:readSetting("plugins_disabled") or {}

for _, name in ipairs({
    "archiveviewer",
    "autodim",
    "autostandby",
    "autosuspend",
    "autoturn",
    "autowarmth",
    "batterystat",
    "bookshortcuts",
    "calibre",
    "cloudstorage",
    "coverbrowser",
    "coverimage",
    "docsettingtweak",
    "exporter",
    "externalkeyboard",
    "hello",
    "httpinspector",
    "japanese",
    "keepalive",
    "kosync",
    "movetoarchive",
    "newsdownloader",
    "opds",
    "perceptionexpander",
    "qrclipboard",
    "readtimer",
    "systemstat",
    "terminal",
    "texteditor",
    "timesync",
    "wallabag",
}) do
    disabled[name] = true
end

for _, name in ipairs({
    "kobo_remote",
    "kosyncthing_plus",
    "statistics",
}) do
    disabled[name] = nil
end
G_reader_settings:saveSetting("plugins_disabled", disabled)
G_reader_settings:saveSetting("SSH_allow_no_password", false)
G_reader_settings:saveSetting("SSH_autostart", true)
G_reader_settings:saveSetting("SSH_force_kill_clients", true)
G_reader_settings:saveSetting("SSH_key_only_auth", true)
G_reader_settings:saveSetting("SSH_port", "2222")

G_reader_settings:saveSetting("syncthing_autostart_mode", "off")
G_reader_settings:saveSetting("syncthing_auto_start_charging", false)
G_reader_settings:saveSetting("syncthing_network_access", "lan")
G_reader_settings:saveSetting("syncthing_notifications_enabled", true)
G_reader_settings:saveSetting("syncthing_periodic_sync_enabled", false)
G_reader_settings:saveSetting("syncthing_periodic_sync_interval_min", 60)
G_reader_settings:saveSetting("syncthing_resource_profile", "low")

local remote = G_reader_settings:readSetting("kobo_remote") or {}
remote.disable_auto_connect_after_connect = true
remote.disable_auto_detection_after_connect = true
remote.enable_auto_connect_polling = false
remote.enable_auto_detection_polling = true
remote.enable_bluetooth_auto_resume = true
remote.show_device_ready_notifications = false
G_reader_settings:saveSetting("kobo_remote", remote)
