# KOReader Appliance

Run `koreader-appliance devices` to see which readers are safe to use now.

KOReader Appliance builds reproducible KOReader-first readers with verified
backups, key-only SSH, recovery paths, format profiles, and runtime evidence.
The daily path is small:

```text
power → vendor hardware initialization → KOReader → current book
```

## Current win

The Kobo Clara BW adapter reproduces the responsive P365 migration that runs
KOReader as the daily interface. The automated core already covers detection,
hash-verified backup, keyed root-package generation, additive staging,
recovery markers, pinned SSH configuration, and whole-page manga settings.

| Adapter | State | Safe action now |
|---|---|---|
| Kobo Clara BW (P365) | Hardware beta | Detect, back up, build, and stage |
| Other Kobo models | Scaffold required | Add and test a model adapter |
| Kindle, PocketBook, reMarkable, Android | Framework only | Add a vendor-specific boot adapter |

“Framework only” blocks installation. It does not guess that unrelated boot
chains, display drivers, or recovery mechanisms work like Kobo.

## First 10 minutes

1. Create the environment.

   ```sh
   python3 -m venv .venv
   . .venv/bin/activate
   python -m pip install -e .
   ```

2. Put a manifest at `~/.config/koreader-appliance/kobo-clara-bw.toml`,
   starting from `profiles/kobo-clara-bw/appliance.toml.example`. Then run the
   complete safe setup (pass the mount explicitly when it is not auto-detected):

   ```sh
   koreader-appliance kobo-clara-bw /Volumes/KOBOeReader --yes
   ```

   This detects the reader, creates or verifies the backup named by the
   manifest, and applies its pinned desired state. The mutating step requires
   `--yes`.

3. Detect the mounted reader without changing it.

   ```sh
   koreader-appliance detect /Volumes/KOBOeReader
   ```

4. Create and hash the complete accessible-storage backup.

   ```sh
   koreader-appliance backup \
     /Volumes/KOBOeReader \
     ~/ReaderBackups/clara-before
   ```

5. Keep `~/ReaderBackups/clara-before/backup-manifest.json`. Staging refuses
   to proceed without that matching, hash-valid manifest.

## Build without committing secrets

Generate the device installer outside the checkout:

```sh
koreader-appliance build-kobo-root \
  --device kobo-clara-bw \
  --authorized-key ~/.ssh/id_reader.pub \
  --scp ~/ReaderToolchain/arm/scp \
  --sftp-server ~/ReaderToolchain/arm/sftp-server \
  --rsync ~/ReaderToolchain/arm/rsync \
  --output ~/ReaderBuilds/clara
```

This takes about 2 seconds after the three verified ARM binaries exist. The
command creates a unique host key, embeds its private half only in
`KoboRoot.tgz`, and exports the public fingerprint beside the installer.

## Stage without activating

Copy KOReader and the generated package while the reader is mounted:

```sh
koreader-appliance stage /Volumes/KOBOeReader \
  --koreader ~/Downloads/koreader-kobo.zip \
  --root-package ~/ReaderBuilds/clara/KoboRoot.tgz \
  --backup-manifest ~/ReaderBackups/clara-before/backup-manifest.json
```

Staging is additive. It creates the folder library, places new settings under
`settings.reader.lua.pending`, and does not eject, reboot, delete, or toggle
Wi-Fi. Kobo activation starts only after an explicit safe eject.

## Declarative appliance manifest

For a repeatable desired state, keep the archive and generated root package
outside the checkout and describe their exact hashes in a TOML manifest. The
backup manifest is required, so applying remains behind the same verified
backup gate as manual staging:

```sh
koreader-appliance plan /Volumes/KOBOeReader \
  --manifest profiles/kobo-clara-bw/appliance.toml
koreader-appliance apply /Volumes/KOBOeReader \
  --manifest profiles/kobo-clara-bw/appliance.toml --yes
```

`plan` is read-only. `apply` detects the adapter, verifies the backup and both
SHA-256 pins, then performs only additive staging. Re-running it is a no-op;
it never deletes files or changes Wi-Fi. Start from
`profiles/kobo-clara-bw/appliance.toml.example`.

## Prove the live result

Run one non-disruptive validation after the reader boots and Wi-Fi is manually
enabled:

```sh
koreader-appliance validate-live \
  --host clara \
  --build-manifest ~/ReaderBuilds/clara/build-manifest.json \
  --evidence ~/ReaderEvidence/clara
```

The command proves the pinned client policy, host fingerprint, root login,
KOReader and watchdog health, installed binary hashes, SFTP, SCP, and additive
rsync. It does not toggle Wi-Fi, reboot, or claim to see physical hardware.

## Safety boundary

Before installation:

1. Detection must match one hardware adapter.
2. The backup must remain outside the mounted reader.
3. Every backup file must still match its stored SHA-256 hash.

During daily use:

1. Wi-Fi changes only when the reader changes it.
2. SSH uses a unique pinned host key and public-key-only login.
3. Physical tests remain separate from remote evidence.

Read [architecture](docs/architecture.md), [device adapters](docs/adding-a-device.md),
[recovery](docs/recovery.md), and [security](SECURITY.md) before adding hardware.

Next: run `koreader-appliance devices` from this checkout.
