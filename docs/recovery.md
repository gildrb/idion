# Recovery

The stable profile always boots to Nickel before KOReader is launched. A
KOReader failure cannot take ownership of the boot path.

## Reachable over SSH

1. Copy KOReader's crash log and `.koreader-appliance.json` off-device.
2. Exit KOReader or reboot into Nickel.
3. Re-run the pinned setup or replace `.adds/koreader` with
   `.adds/koreader.previous` while mounted.
4. Launch KOReader manually and repeat the failed operation.

## Not reachable over SSH

1. Power off the reader.
2. Boot normally into Nickel.
3. Connect USB and mount storage.
4. Re-run the pinned setup or restore the verified off-device backup.
5. Safely eject before launching KOReader.

## Full restore

Use the off-device storage backup and the official model-specific firmware.
Neither belongs in this repository. Verify the hardware product code before
applying firmware.

The legacy `launch.mode = "autostart"` profile still recognizes
`.kobo/KOReader-autostart-disabled`, but it is not the stable production
profile.
