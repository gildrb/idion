# KOReader Appliance

KOReader Appliance installs [KOReader](https://github.com/koreader/koreader), a
free and open-source reading application, onto a supported e-reader from your
computer. It takes a full verified backup before changing the mounted reader.
A TOML configuration records the input paths and hashes so the same state can
be reproduced.

Start with [Setup](#setup): find your model, prepare its manifest, and run the
one-shot command after mounting the reader.

### What changes compared to stock

The staged `KoboRoot.tgz` is an additive overlay for the supported Kobo
adapter. It changes the following parts of the reader:

- `/etc/hosts` maps Kobo and Rakuten store, account, sync, firmware-update,
  and analytics endpoints such as `api.kobobooks.com`, `auth.kobobooks.com`,
  `device.kobo.com`, `firmware.kobo.com`, `storeapi.kobo.com`,
  `www.kobo.com`, and `www.google-analytics.com` to `0.0.0.0`. KOReader
  networking, dictionaries, Wikipedia, SSH, and user-selected services remain
  unrestricted according to the overlay's hosts file.
- `on-animator.sh` starts `koreader-autostart.sh` during boot. That script waits
  for Nickel and the onboard storage, then starts KOReader after Nickel has
  initialized the hardware. A disable marker, USB or external power at boot,
  an incomplete installation, or two early KOReader failures keeps the reader
  in Nickel.
- The SSH init script starts `sshd` only when `.kobo/ssh-enabled` exists.
  `sshd_config` permits public-key authentication only, disables password
  authentication, and uses `/etc/ssh/ssh_host_ed25519_key`. The root-package
  builder generates a new Ed25519 host key for each build. It also installs
  the `scp`, `sftp-server`, and `rsync` binaries that you provide, and starts
  a watchdog that retries `sshd` if it stops.
- The recovery marker
  `/mnt/onboard/.kobo/KOReader-autostart-disabled` prevents the autostart
  script from launching KOReader. Remove it only after the reader is stable
  and a manual KOReader launch succeeds.

The overlay does not replace Nickel firmware, the Kobo boot chain, or device
drivers. It does not delete existing files, change Wi-Fi settings, reboot, or
eject the reader. The off-device backup remains the source for restoring the
previous reader state.

### What this does and does not do

The commands run locally, create no accounts, upload nothing, and make no
network calls. They detect one adapter, create or verify an off-device backup,
verify SHA-256 pins, and stage files additively. `plan` is read-only.
`validate-live` is separate and connects only when explicitly run.

### Hardware status

| Adapter | State | Supported operations |
|---|---|---|
| Kobo Clara BW (P365) | Verified | Detect, back up, build, and stage |
| Clara HD, Clara 2E, Clara Colour, Libra H2O, Libra 2, Libra Colour, Nia, Sage, Elipsa 2E, Forma | Unverified | KoboRoot.tgz path; requires `--allow-unverified` |
| Kindle | Blocked | Detect and back up only; jailbreak and KUAL/MRPI adapter required |

Kindle installation is refused. The unverified Kobo adapters use the shared
rootfs and have no physical hardware test evidence.

### Setup

1. Find your model in the table. Create an environment:

   ```sh
   python3 -m venv .venv
   . .venv/bin/activate
   python -m pip install -e .
   ```

2. Build the root package. The repository does not provide the target ARM
   `scp`, `sftp-server`, and `rsync` binaries.

   ```sh
   koreader-appliance build-kobo-root --device kobo-libra-2 \
     --authorized-key ~/.ssh/id_reader.pub \
     --scp ~/ReaderToolchain/arm/scp \
     --sftp-server ~/ReaderToolchain/arm/sftp-server \
     --rsync ~/ReaderToolchain/arm/rsync \
     --output ~/ReaderBuilds/libra
   ```

3. Copy the example manifest, fill in its paths and device ID, then hash the
   KOReader archive and root package:

   ```sh
   mkdir -p ~/.config/koreader-appliance
   cp adapters/_kobo-common/profiles/appliance.toml.example \
     ~/.config/koreader-appliance/kobo-libra-2.toml
   sha256sum ~/Downloads/koreader-kobo.zip ~/ReaderBuilds/libra/KoboRoot.tgz
   ```

   Download KOReader from its
   [release files](https://github.com/koreader/koreader/releases). Put both
   hashes and the backup manifest path in the TOML file.

4. Mount the reader and run setup:

   ```sh
   koreader-appliance kobo-libra-2 /Volumes/KOBOeReader \
     --yes --allow-unverified
   ```

   Setup detects the reader, verifies or creates the backup, checks both pins,
   and applies the manifest. The backup stays outside the reader.

Manual backup, staging, planning, applying, live validation, and recovery
instructions are in [manual operations](docs/manual-operations.md).

Read [recovery](docs/recovery.md) before setup. Then fill in the manifest and
run the setup command above.
