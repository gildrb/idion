# Kobo Remote Bluetooth-only variant

Upstream: `OGKevin/kobo.koplugin`

Upstream commit: `9ce2eb3d78771327aa2428251213a8b94d727209`

Local variant: `0.4.1-appliance.1`

This package retains the upstream Bluetooth manager and removes the virtual
Nickel library, DRM cache, and Kobo/KOReader reading-state synchronization.

Migration-specific behavior:

- Bluetooth resumes after wake only when it was enabled before suspend.
- The official Kobo Remote reconnect is detected automatically.
- The remote's forward and back buttons work without an initial mapping step.
- Explicit custom button bindings override the built-in defaults.
- Bluetooth may temporarily power Wi-Fi for MTK initialization, then restores
  the exact Wi-Fi state observed before initialization.
- No code in this package performs network requests.
- Suspend-time D-Bus requests have hard one-second reply deadlines.
- Input-device discovery after reconnect is scheduled asynchronously and never
  sleeps on KOReader's UI thread.

Default official Kobo Remote mapping:

- `KEY_DOWN` / code 108: next page
- `KEY_UP` / code 103: previous page
