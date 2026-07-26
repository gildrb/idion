# KOReader Appliance

KOReader Appliance installs [KOReader](https://github.com/koreader/koreader), a
free and open-source reading application, onto a supported e-reader from your
computer. It takes a full verified backup before changing the mounted reader.
A TOML configuration records the input paths and hashes so the same state can
be reproduced.

## What this does and does not do

- The setup, backup, build, and staging commands run on your computer.
- They do not create accounts, upload files, or make network calls.
- Changes are additive. The backup and recovery marker provide restore and
  disable paths.
- `validate-live` is separate and connects to a reader only when you run it.

## Hardware status

The Kobo Clara BW adapter has been tested on a P365 device. The other Kobo
adapters have verified model markers but are untested on physical hardware.
The core provides detection, hash-verified backup, keyed root-package
generation, additive staging, recovery markers, SSH configuration, and
document profiles.

| Adapter | State | Supported operations |
|---|---|---|
| Kobo Clara BW (P365) | Hardware beta | Detect, back up, build, and stage |
| Kobo Clara HD (N249), Clara 2E (N506), Clara Colour (N367), Libra H2O (N873), Libra 2 (N418), Libra Colour (N428), Nia (N306), Sage (N778), Elipsa 2E (N605), Forma (N782) | Staging beta | KoboRoot.tgz path; untested, requires `--allow-untested` |
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
   hashes. Download the KOReader Kobo archive from
   [KOReader's releases](https://github.com/koreader/koreader/releases), and
   hash the archive and root package locally:

   ```sh
   mkdir -p ~/.config/koreader-appliance
   cp adapters/kobo-clara-bw/profiles/appliance.toml.example \
     ~/.config/koreader-appliance/kobo-libra-2.toml
   sha256sum ~/Downloads/koreader-kobo.zip ~/ReaderBuilds/libra/KoboRoot.tgz
   ```

   Put those 64-character values in `[koreader].sha256` and
   `[root_package].sha256`, and set `device` plus the backup manifest path.

4. Build the root package before setup:

   ```sh
   koreader-appliance build-kobo-root \
     --device kobo-libra-2 \
     --authorized-key ~/.ssh/id_reader.pub \
     --scp ~/ReaderToolchain/arm/scp \
     --sftp-server ~/ReaderToolchain/arm/sftp-server \
     --rsync ~/ReaderToolchain/arm/rsync \
     --output ~/ReaderBuilds/libra
   ```

   The repository does not provide these target-compatible ARM binaries.
   Obtain them from your own ARM toolchain or another source you trust. This
   build is for key-only SSH and is required by the current manifest flow.

5. Run the one-shot setup. It finds a matching common mount automatically; pass
   the mount path explicitly if needed:

   ```sh
   koreader-appliance <device> --yes
   koreader-appliance kobo-libra-2 /Volumes/KOBOeReader --yes --allow-untested
   ```

   Setup detects the reader, creates or verifies the backup named by the
   manifest, verifies both pins, and applies the desired state. Untested Kobo
   adapters require `--allow-untested`; the mutating step always requires
   `--yes`.

6. To inspect a reader without changing it, plan first:

   ```sh
   koreader-appliance plan /Volumes/KOBOeReader \
     --manifest ~/.config/koreader-appliance/kobo-libra-2.toml
   ```

The setup flow keeps the backup outside the reader and never deletes files,
reboots, ejects, or changes Wi-Fi. Staging-beta Kobo models use the shared Kobo
rootfs until a model-specific rootfs is available.

## Manual operations

To back up and stage without the one-shot command:

```sh
koreader-appliance backup /Volumes/KOBOeReader ~/ReaderBackups/clara-before
koreader-appliance stage /Volumes/KOBOeReader \
  --koreader ~/Downloads/koreader-kobo.zip \
  --root-package ~/ReaderBuilds/clara/KoboRoot.tgz \
  --backup-manifest ~/ReaderBackups/clara-before/backup-manifest.json
```

Staging is additive. It creates the folder library, places new settings under
`settings.reader.lua.pending`, and does not eject, reboot, delete, or toggle
Wi-Fi. For read-only desired-state inspection:

```sh
koreader-appliance plan /Volumes/KOBOeReader \
  --manifest adapters/kobo-clara-bw/profiles/appliance.toml
koreader-appliance apply /Volumes/KOBOeReader \
  --manifest adapters/kobo-clara-bw/profiles/appliance.toml --yes
```

`plan` is read-only. `apply` detects the adapter, verifies the backup and both
SHA-256 pins, then performs only additive staging. Re-running it is a no-op.
Start from `adapters/kobo-clara-bw/profiles/appliance.toml.example`.

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
