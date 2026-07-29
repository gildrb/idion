# KOReader Appliance

KOReader Appliance installs [KOReader](https://github.com/koreader/koreader), a
free and open-source reading application, onto a supported e-reader from your
computer. It takes a full verified backup before changing the mounted reader.
A TOML configuration records the input paths and hashes so the same state can
be reproduced.

Start with [Setup](#setup): find your model, prepare its manifest, and run the
one-shot command after mounting the reader.

### Stable profile

The recommended `launch.mode = "nickelmenu"` profile keeps Kobo's firmware,
boot chain, hardware initialization, sleep, and recovery interface intact.
After a normal boot, launch KOReader with one tap from NickelMenu. This removes
the custom boot takeover from the daily reliability path.

The generated `KoboRoot.tgz` contains only NickelMenu's pinned upstream binary
and a stock-compatible `/etc/hosts`. Kobo account, store, library sync, and
firmware updates remain available. It does not install the autostart manager
or root SSH watchdog.

KOReader is replaced transactionally: a complete new tree is copied and
synced before activation, mutable reading state is carried forward, and the
previous installation remains at `.adds/koreader.previous`. A power loss or
bad KOReader build therefore falls back to Nickel instead of compromising the
Kobo boot path. The Clara BW adapter adds a Bluetooth-only plugin pinned to a
documented upstream commit; suspend calls have reply deadlines and reconnect
discovery never sleeps on the UI thread.

KOReader's maintained Dropbear service provides key-only SSH on port 2222 when
KOReader and Wi-Fi are running. No password login, rootfs SSH daemon, or
watchdog is installed.

### What this does and does not do

Commands run locally, create no accounts, upload nothing, and make no network
calls. They detect one adapter, verify an off-device backup and SHA-256 pins,
then stage a transactional KOReader tree and additive root installer. `plan`
is read-only. `validate-live` connects only when explicitly run.

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

2. Download the Kobo KOReader release and the stable NickelMenu
   `KoboRoot.tgz`. Build the minimal pinned root package:

   ```sh
   koreader-appliance build-kobo-root --device kobo-clara-bw \
     --launch-mode nickelmenu \
     --nickelmenu-package ~/Downloads/NickelMenu-KoboRoot.tgz \
     --output ~/ReaderBuilds/clara-bw
   ```

3. Copy the example manifest, fill in its paths and device ID, then hash the
   KOReader archive and root package:

   ```sh
   mkdir -p ~/.config/koreader-appliance
   cp adapters/_kobo-common/profiles/appliance.toml.example \
     ~/.config/koreader-appliance/kobo-clara-bw.toml
   sha256sum ~/Downloads/koreader-kobo.zip \
     ~/ReaderBuilds/clara-bw/KoboRoot.tgz
   ```

   Download KOReader from its
   [release files](https://github.com/koreader/koreader/releases). Put both
   hashes and the backup manifest path in the TOML file.

4. Mount the reader and run setup:

   ```sh
   koreader-appliance kobo-clara-bw /Volumes/KOBOeReader --yes
   ```

   Setup detects the reader, verifies or creates the backup, checks both pins,
   and applies the manifest. The backup stays outside the reader.

Manual backup, staging, planning, applying, live validation, and recovery
instructions are in [manual operations](docs/manual-operations.md).

Read [recovery](docs/recovery.md) before setup. Then fill in the manifest and
run the setup command above. A deployment is not called hardware-stable until
it passes the [acceptance protocol](docs/acceptance.md).
