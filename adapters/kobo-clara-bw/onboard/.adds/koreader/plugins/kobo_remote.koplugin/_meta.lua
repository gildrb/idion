local _ = require("gettext")

return {
    id = "kobo_remote.koplugin",
    name = "kobo_remote",
    fullname = _("Kobo Bluetooth Remote"),
    description = _([[Bluetooth-only support for the official Kobo Remote.
Keeps Nickel library and reading-state synchronization disabled.]]),
    author = "OGKevin; Bluetooth-only migration variant",
    version = "0.4.1-appliance.1",
    supported_platforms = { "kobo" },
}
