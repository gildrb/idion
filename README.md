# KOReader Appliance

KOReader Appliance installs [KOReader](https://github.com/koreader/koreader), a
free and open-source reading application, onto a supported e-reader from your
computer. It takes a full verified backup before changing the mounted reader.
A TOML configuration records the input paths and hashes so the same state can
be reproduced.

Start with [Setup](#setup): find your model, prepare its manifest, and run the
one-shot command after mounting the reader.

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

1. Create an environment from a repository clone:

   ```sh
   python3 -m venv .venv
   . .venv/bin/activate
   python -m pip install -e .
   ```

2. Download the KOReader Kobo archive and NickelMenu `KoboRoot.tgz` yourself.
   The tool makes no network calls. Mount the reader, then run one command:

   ```sh
   koreader-appliance setup kobo-clara-bw /Volumes/KOBOeReader \
     --koreader ~/Downloads/koreader-kobo.zip \
     --launch-mode nickelmenu \
     --nickelmenu-package ~/Downloads/NickelMenu-KoboRoot.tgz \
     --yes
   ```

   Setup detects the adapter, builds the pinned root package under
   `~/.local/state/koreader-appliance/`, computes the archive hashes, writes
   `~/.config/koreader-appliance/kobo-clara-bw.toml`, creates and verifies an
   off-device backup, and applies the manifest. The generated manifest path is
   printed. Repeating the command re-verifies the same state without
   redeploying it.

   For autostart mode, supply `--authorized-key`, `--scp`, `--sftp-server`, and
   `--rsync` instead of `--nickelmenu-package`. The backup stays outside the
   reader. An existing manifest may be refreshed with only the artifact flags
   that changed; with no flags, setup uses it unchanged.

Manual backup, staging, planning, applying, live validation, and recovery
instructions are in [manual operations](docs/manual-operations.md).

Read [recovery](docs/recovery.md) before setup. Then fill in the manifest and
run the setup command above. A deployment is not called hardware-stable until
it passes the [acceptance protocol](docs/acceptance.md).
