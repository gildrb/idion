# Manual operations

Use these commands when the one-shot setup flow is not suitable.

### Backup and stage

```sh
koreader-appliance backup /Volumes/KOBOeReader ~/ReaderBackups/clara-before
koreader-appliance stage /Volumes/KOBOeReader \
  --koreader ~/Downloads/koreader-kobo.zip \
  --root-package ~/ReaderBuilds/clara/KoboRoot.tgz \
  --backup-manifest ~/ReaderBackups/clara-before/backup-manifest.json \
  --launch-mode nickelmenu \
  --authorized-key ~/.ssh/id_reader.pub
```

NickelMenu staging writes a complete `.adds/koreader.staging` tree, syncs it,
preserves mutable state, activates it, and retains the previous tree. It also
creates library folders and the NickelMenu launch entry. It does not eject,
reboot, or toggle Wi-Fi.

### Plan and apply

```sh
koreader-appliance plan /Volumes/KOBOeReader \
  --manifest ~/.config/koreader-appliance/kobo-libra-2.toml
koreader-appliance apply /Volumes/KOBOeReader \
  --manifest ~/.config/koreader-appliance/kobo-libra-2.toml --yes
```

`plan` is read-only. `apply` detects the adapter, verifies the backup and both
SHA-256 pins, then converges the declared state. Re-running it preserves
current KOReader settings and does not redeploy an unchanged KOReader tree.

### Live validation

Run validation after KOReader launches and Wi-Fi is manually enabled. The
stable profile uses KOReader SSH on port 2222 rather than rootfs OpenSSH:

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

The stable profile never autostarts KOReader. Exit KOReader or reboot to reach
Nickel. If a new KOReader tree fails, restore `.adds/koreader.previous` or
re-run setup with the last pinned archive. Keep the off-device backup for a
full restore. See [recovery](recovery.md).
