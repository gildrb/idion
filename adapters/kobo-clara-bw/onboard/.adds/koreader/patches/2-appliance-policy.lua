local disabled = G_reader_settings:readSetting("plugins_disabled") or {}

local known_plugins = {
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
    "kobo_remote",
    "kosyncthing_plus",
    "readingstreak",
    "statistics",
}

local function disable_known_plugins()
    for _, name in ipairs(known_plugins) do
        disabled[name] = true
    end
end

local enumerated = false
local enumeration_ok = pcall(function()
    local lfs = require("lfs")
    local data_storage = require("datastorage")
    local paths = {
        lfs.currentdir() .. "/plugins",
        data_storage:getDataDir() .. "/plugins",
    }
    local extra_paths = G_reader_settings:readSetting("extra_plugin_paths")
    if type(extra_paths) == "table" then
        for _, path in ipairs(extra_paths) do
            table.insert(paths, path)
        end
    elseif type(extra_paths) == "string" then
        table.insert(paths, extra_paths)
    end
    for _, path in ipairs(paths) do
        local path_ok = pcall(function()
            for entry in lfs.dir(path) do
                if entry ~= "." and entry ~= ".." and entry:sub(-9) == ".koplugin" then
                    disabled[entry:sub(1, -10)] = true
                end
            end
        end)
        enumerated = enumerated or path_ok
    end
end)
if not enumeration_ok or not enumerated then
    disable_known_plugins()
end

G_reader_settings:saveSetting("plugins_disabled", disabled)
G_reader_settings:saveSetting("SSH_allow_no_password", false)
G_reader_settings:saveSetting("SSH_autostart", false)
G_reader_settings:saveSetting("SSH_force_kill_clients", true)
G_reader_settings:saveSetting("SSH_key_only_auth", true)
G_reader_settings:saveSetting("SSH_port", "2222")

local remote = G_reader_settings:readSetting("kobo_remote") or {}
remote.disable_auto_connect_after_connect = true
remote.disable_auto_detection_after_connect = true
remote.enable_auto_connect_polling = false
remote.enable_auto_detection_polling = true
remote.enable_bluetooth_auto_resume = true
remote.show_device_ready_notifications = false
G_reader_settings:saveSetting("kobo_remote", remote)
