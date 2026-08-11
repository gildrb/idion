# idion

Puts [KOReader](https://github.com/koreader/koreader) on a Kobo and strips the rest.

One command from a mounted reader: verified backup, pinned artifacts, installed, done.

### Does

- Backs up the reader off-device and verifies the backup before writing anything.
- Pins every artifact by SHA-256 in `~/.config/koreader-appliance/<device>.toml`, so the same install is reproducible.
- Stages KOReader transactionally, keeping the previous tree for rollback.
- Blackholes Nickel's analytics, store/sync, and silent-upgrade endpoints, and starts Nickel in airplane and sideloaded mode.
- Leaves the default boot chain stock: Kobo, NickelMenu, KOReader.

### Does not

- No network calls during setup. Download the archives yourself.
  `validate-live` connects only when explicitly run.
- No telemetry, no accounts, no uploads, no crash reports.
- No plugin enabled. `kobo_remote` ships present and disabled.
- No service enabled in the default NickelMenu path. SSH does not autostart.

### Install

```sh
git clone https://github.com/gildrb/koreader-appliance
cd koreader-appliance
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

Download the [KOReader Kobo archive](https://github.com/koreader/koreader/releases) and [NickelMenu `KoboRoot.tgz`](https://github.com/pgaskin/NickelMenu/releases) yourself.

### Use

Mount the reader, then:

```sh
koreader-appliance setup kobo-clara-bw /Volumes/KOBOeReader \
  --koreader ~/Downloads/koreader-kobo.zip \
  --nickelmenu-package ~/Downloads/NickelMenu-KoboRoot.tgz \
  --yes
```

Eject, let the reader apply the update, then use NickelMenu to start KOReader.
Done.

Setup detects the adapter, builds the root package, computes the hashes, writes the manifest, backs up, and applies. Run it again whenever; it re-verifies the same state instead of reinstalling it. Pass only the artifact flags that changed to refresh an existing manifest; pass none to reuse it.

Autostart into KOReader is a separate launch mode requiring `--launch-mode autostart` with `--authorized-key`, `--scp`, `--sftp-server`, and `--rsync` instead of `--nickelmenu-package`. It starts the root OpenSSH service. NickelMenu is the tested path.

### Hardware

| Adapter | State | Operations |
| --- | --- | --- |
| Kobo Clara BW (P365) | Verified | Detect, back up, build, stage |
| Clara HD, Clara 2E, Clara Colour, Libra H2O, Libra 2, Libra Colour, Nia, Sage, Elipsa 2E, Forma | Unverified | Detect, back up, build, stage with `--allow-unverified` |
| Kindle | Blocked | Detect and back up only; installation refused |

Unverified adapters share the Kobo rootfs and have no hardware test evidence. The privacy defaults are covered by tests and fake-mount runs, not by a hardware surveillance audit.

### Docs

[Recovery](docs/recovery.md), read before setup<br>
[Manual operations](docs/manual-operations.md)<br>
[Acceptance protocol](docs/acceptance.md)<br>
[Architecture](docs/architecture.md)<br>
[Adding a device](docs/adding-a-device.md)

### Safety

Keep credentials, private keys, Wi-Fi data, books, firmware images, backups, and generated installers out of Git. Every write to a mounted reader follows device detection and a verified backup. A deployment is not hardware-stable until it passes the [acceptance protocol](docs/acceptance.md).
