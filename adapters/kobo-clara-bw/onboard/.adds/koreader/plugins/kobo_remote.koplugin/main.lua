--- Bluetooth-only Kobo integration for KOReader.
---
--- This local variant intentionally omits Nickel library and reading-state
--- synchronization. It retains only the upstream Bluetooth manager, input
--- isolation, reconnect handling, and configurable button bindings.

local KoboBluetooth = require("src/kobo_bluetooth")
local WidgetContainer = require("ui/widget/container/widgetcontainer")

local default_settings = {
    bluetooth_key_bindings = {},
    disable_auto_connect_after_connect = true,
    disable_auto_detection_after_connect = true,
    dismiss_widgets_on_button = false,
    enable_auto_connect_polling = false,
    enable_auto_detection_polling = true,
    enable_bluetooth_auto_resume = true,
    official_kobo_remote_defaults = true,
    paired_devices = {},
    show_bluetooth_footer_status = true,
    show_device_ready_notifications = false,
}

local bluetooth_instance = nil

local KoboRemote = WidgetContainer:extend({
    name = "kobo_remote",
    is_doc_only = false,
    default_settings = default_settings,
})

local function copyDefault(value)
    if type(value) ~= "table" then
        return value
    end

    local copy = {}
    for key, item in pairs(value) do
        copy[key] = item
    end
    return copy
end

function KoboRemote:init()
    self:loadSettings()

    if not bluetooth_instance then
        bluetooth_instance = KoboBluetooth:create()
    end

    self.kobo_bluetooth = bluetooth_instance
    table.insert(self, self.kobo_bluetooth)
    self.kobo_bluetooth:initWithPlugin(self)
    self.ui.menu:registerToMainMenu(self)
    self:onDispatcherRegisterActions()
end

function KoboRemote:loadSettings()
    self.settings = G_reader_settings:readSetting("kobo_remote") or {}

    for key, default_value in pairs(self.default_settings) do
        if self.settings[key] == nil then
            self.settings[key] = copyDefault(default_value)
        end
    end
end

function KoboRemote:saveSettings()
    G_reader_settings:saveSetting("kobo_remote", self.settings)
    G_reader_settings:flush()
end

function KoboRemote:addToMainMenu(menu_items)
    if self.kobo_bluetooth then
        self.kobo_bluetooth:addToMainMenu(menu_items)
    end
end

function KoboRemote:onDispatcherRegisterActions()
    if self.kobo_bluetooth then
        self.kobo_bluetooth:registerPairedDevicesWithDispatcher()
        self.kobo_bluetooth:registerBluetoothActionsWithDispatcher()
    end
end

return KoboRemote
