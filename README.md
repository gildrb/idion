# KOReader Appliance

Run `koreader-appliance devices` to see which readers are safe to use now.

KOReader Appliance builds a pinned KOReader install on a mounted e-reader after
a verified backup. It configures key-only SSH, uses additive staging, and
provides a recovery marker.
The daily path is small:

```text
power → vendor hardware initialization → KOReader → current book
```

## Hardware status

The Kobo Clara BW adapter has been tested on a P365 device. The other Kobo
adapters have verified model markers but are untested on physical hardware.
The core provides detection, hash-verified backup, keyed root-package
generation, additive staging, recovery markers, SSH configuration, and
document profiles.

| Adapter | State | Supported operations |
|---|---|---|
| Kobo Clara BW (P365) | Hardware beta | Detect, back up, build, and stage |
| Kobo Clara HD (N249) | Staging beta | KoboRoot.tgz path; untested, requires `--allow-untested` |
| Kobo Clara 2E (N506) | Staging beta | KoboRoot.tgz path; untested, requires `--allow-untested` |
| Kobo Clara Colour (N367) | Staging beta | KoboRoot.tgz path; untested, requires `--allow-untested` |
| Kobo Libra H2O (N873) | Staging beta | KoboRoot.tgz path; untested, requires `--allow-untested` |
| Kobo Libra 2 (N418) | Staging beta | KoboRoot.tgz path; untested, requires `--allow-untested` |
| Kobo Libra Colour (N428) | Staging beta | KoboRoot.tgz path; untested, requires `--allow-untested` |
| Kobo Nia (N306) | Staging beta | KoboRoot.tgz path; untested, requires `--allow-untested` |
| Kobo Sage (N778) | Staging beta | KoboRoot.tgz path; untested, requires `--allow-untested` |
| Kobo Elipsa 2E (N605) | Staging beta | KoboRoot.tgz path; untested, requires `--allow-untested` |
| Kobo Forma (N782) | Staging beta | KoboRoot.tgz path; untested, requires `--allow-untested` |
| Kindle | Framework only | Detect and back up only; jailbreak and KUAL/MRPI adapter required |

“Framework only” blocks installation. It does not guess that unrelated boot
chains, display drivers, or recovery mechanisms work like Kobo.

## First 10 minutes

1. Find your device in the table above. Kindle detection and backup work, but
   installation is intentionally refused until a Kindle jailbreak and vendor
   adapter exist.

2. Create the environment.

   ```sh
   python3 -m venv .venv
   . .venv/bin/activate
   python -m pip install -e .
   ```

3. Copy the example manifest to
   `~/.config/koreader-appliance/<device>.toml`, then fill in the paths and
   hashes. Download the Kobo archive from
   [KOReader's releases](https://github.com/koreader/koreader/releases), and
   hash both inputs locally:

   ```sh
   mkdir -p ~/.config/koreader-appliance
   cp profiles/kobo-clara-bw/appliance.toml.example \
     ~/.config/koreader-appliance/kobo-libra-2.toml
   sha256sum ~/Downloads/koreader-kobo.zip ~/ReaderBuilds/libra/KoboRoot.tgz
   ```

   Put those 64-character values in `[koreader].sha256` and
   `[root_package].sha256`, and set `device` plus the backup manifest path.

4. Run the one-shot setup. It finds a matching common mount automatically; pass
   the mount path explicitly if needed:

   ```sh
   koreader-appliance <device> --yes
   koreader-appliance kobo-libra-2 /Volumes/KOBOeReader --yes --allow-untested
   ```

   Setup detects the reader, creates or verifies the backup named by the
   manifest, verifies both pins, and applies the desired state. Untested Kobo
   adapters require `--allow-untested`; the mutating step always requires
   `--yes`.

5. To inspect a reader without changing it, plan first:

   ```sh
   koreader-appliance plan /Volumes/KOBOeReader \
     --manifest ~/.config/koreader-appliance/kobo-libra-2.toml
   ```

The setup flow keeps the backup outside the reader and never deletes files,
reboots, ejects, or changes Wi-Fi.

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

The command creates a unique host key, embeds its private half only in
`KoboRoot.tgz`, and exports the public fingerprint beside the installer.
Staging-beta Kobo models reuse the Clara rootfs template until a
model-specific rootfs is available. The generated build manifest records the
host key fingerprint.

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

## Validate a live reader

Run live validation after the reader boots and Wi-Fi is manually enabled:

```sh
koreader-appliance validate-live \
  --host clara \
  --build-manifest ~/ReaderBuilds/clara/build-manifest.json \
  --evidence ~/ReaderEvidence/clara
```

The command checks the pinned client policy, host fingerprint, root login,
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
