return {
    -- An unexpected KOReader failure returns control to the bounded boot
    -- circuit instead of hiding the crash behind an endless relaunch loop.
    ["dev_abort_on_crash"] = true,

    -- Wi-Fi changes only when the reader explicitly changes it.
    ["auto_disable_wifi"] = false,
    ["auto_restore_wifi"] = false,
    ["wifi_enable_action"] = "prompt",

    -- The first boot opens the folder library. Later boots return to the most
    -- recently opened book without requiring a vendor library database.
    ["home_dir"] = "/mnt/onboard/Books",
    ["start_with"] = "last",

    -- Readable EPUB defaults without depending on a user-supplied font.
    ["copt_font_size"] = 24,
    ["copt_h_page_margins"] = { 0, 0 },
    ["copt_t_page_margin"] = 10,
    ["copt_b_page_margin"] = 10,
    ["copt_line_spacing"] = 100,
    ["hyphenation"] = true,

    -- Safe PDF default: one complete native MuPDF page per turn. Technical
    -- documents may opt into crop or multi-column mode per book.
    ["kopt_text_wrap"] = 0,
    ["kopt_trim_page"] = 0,
    ["kopt_max_columns"] = 1,
    ["kopt_page_scroll"] = 0,
    ["kopt_zoom_mode_genus"] = 4,
    ["kopt_zoom_mode_type"] = 2,
    ["kopt_contrast"] = 1.2,

    -- Preserve the case magnet as a normal KOReader sleep/wake input.
    ["ignore_open_sleepcover"] = false,
    ["ignore_power_sleepcover"] = false,

    -- KOReader's maintained Dropbear service is available for diagnostics
    -- and server snapshots whenever KOReader and Wi-Fi are running. An exit
    -- patch terminates it before USB storage unmounts the data partition.
    ["SSH_allow_no_password"] = false,
    ["SSH_autostart"] = true,
    ["SSH_force_kill_clients"] = true,
    ["SSH_key_only_auth"] = true,
    ["SSH_port"] = "2222",

    ["kobo_remote"] = {
        ["bluetooth_key_bindings"] = {},
        ["enable_auto_connect_polling"] = false,
        ["enable_auto_detection_polling"] = true,
        ["enable_bluetooth_auto_resume"] = true,
        ["official_kobo_remote_defaults"] = true,
        ["paired_devices"] = {},
        ["show_bluetooth_footer_status"] = true,
    },
}
