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
adapter:

- `/etc/hosts` maps Kobo and Rakuten store, account, sync, firmware-update,
  and analytics hosts to `0.0.0.0`, including the hosts listed in
  `adapters/_kobo-common/rootfs/etc/hosts`. KOReader networking, dictionaries,
  Wikipedia, SSH, and user-selected services remain unrestricted.
- `on-animator.sh` starts `koreader-autostart.sh` after Nickel initializes.
  USB or external power, the disable marker, an incomplete install, or two
  early failures keeps the reader in Nickel. The marker is
  `/mnt/onboard/.kobo/KOReader-autostart-disabled`.
- SSH starts only with `.kobo/ssh-enabled`, allows public keys only, and uses
  a new Ed25519 host key per build. The overlay includes the user-provided
  `scp`, `sftp-server`, and `rsync` binaries plus an `sshd` watchdog.

The overlay does not replace Nickel firmware, the Kobo boot chain, or device
drivers. It does not delete existing files, change Wi-Fi settings, reboot, or
eject the reader. The off-device backup remains the source for restoring the
previous reader state.

### What this does and does not do

Commands run locally, create no accounts, upload nothing, and make no network
calls. They detect one adapter, verify an off-device backup and SHA-256 pins,
then stage files additively. `plan` is read-only. `validate-live` connects only
when explicitly run.

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
