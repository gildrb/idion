# Manual operations

Use these commands when the one-shot setup flow is not suitable.

### Backup and stage

```sh
koreader-appliance backup /Volumes/KOBOeReader ~/ReaderBackups/clara-before
koreader-appliance stage /Volumes/KOBOeReader \
  --koreader ~/Downloads/koreader-kobo.zip \
  --root-package ~/ReaderBuilds/clara/KoboRoot.tgz \
  --backup-manifest ~/ReaderBackups/clara-before/backup-manifest.json
```

Staging is additive. It creates library folders, places settings under
`settings.reader.lua.pending`, and does not eject, reboot, delete, or toggle
Wi-Fi.

### Plan and apply

```sh
koreader-appliance plan /Volumes/KOBOeReader \
  --manifest ~/.config/koreader-appliance/kobo-libra-2.toml
koreader-appliance apply /Volumes/KOBOeReader \
  --manifest ~/.config/koreader-appliance/kobo-libra-2.toml --yes
```

`plan` is read-only. `apply` detects the adapter, verifies the backup and both
SHA-256 pins, then performs only additive staging. Re-running it is a no-op.

### Live validation

Run validation after the reader boots and Wi-Fi is manually enabled:

```sh
koreader-appliance validate-live \
  --host clara \
  --build-manifest ~/ReaderBuilds/clara/build-manifest.json \
  --evidence ~/ReaderEvidence/clara
```

The command checks the pinned client policy, host fingerprint, root login,
KOReader and watchdog health, installed binary hashes, SFTP, SCP, and additive
rsync. It does not toggle Wi-Fi, reboot, or claim to see physical hardware.

### Recovery

To disable KOReader autostart, use the recovery command or create
`/mnt/onboard/.kobo/KOReader-autostart-disabled` while the reader is mounted.
Keep the off-device backup for a full restore. See
[recovery](recovery.md) for the reachable and USB recovery paths.
