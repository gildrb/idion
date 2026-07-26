# Recovery

Capture `clara-health.sh` and `clara-logs.sh` before rebooting a reachable Kobo.

## Reachable over SSH

1. Record health and logs.
2. Create `/mnt/onboard/.kobo/KOReader-autostart-disabled`.
3. Reboot once and confirm Nickel remains available.
4. Fix the fault while autostart stays disabled.
5. Remove the marker only after KOReader passes a manual launch.

## Not reachable over SSH

1. Power off the reader.
2. Connect USB before boot so the Clara adapter stays in Nickel recovery.
3. Create `.kobo/KOReader-autostart-disabled` on the mounted storage.
4. Safely eject, then boot once.

## Full restore

Use the off-device storage backup and the official model-specific firmware.
Neither belongs in this repository. Verify the hardware product code before
applying firmware.

