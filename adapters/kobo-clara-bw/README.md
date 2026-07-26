# Kobo Clara BW adapter

Start with `koreader-appliance backup`; do not build or stage an installer
until the backup finishes and its hashes match.

## What works

1. Firmware `4.45.23697` on product `P365` starts KOReader after bounded Nickel
   hardware initialization.
2. A cable at boot or `.kobo/KOReader-autostart-disabled` keeps the device in
   Nickel for recovery.
3. Two early KOReader failures open the launch circuit instead of creating an
   endless crash loop.
4. OpenSSH starts independently, uses a generated Ed25519 host identity, and
   accepts only the supplied operator key from `/.ssh/authorized_keys`.
5. SFTP, SCP, and rsync use explicitly supplied ARM binaries whose hashes are
   recorded in the generated build manifest.

## Required local inputs

1. An official KOReader Kobo archive.
2. One operator public key.
3. Verified ARM builds of `scp`, `sftp-server`, and static `rsync`.
4. A mounted Clara BW that matches the P365 detection marker.

Firmware, private keys, books, and generated installers stay outside Git.

## Physical acceptance

The automated validator cannot see the e-ink panel or operate the cover. A
release still requires observed display stability, ComfortLight intensity and
warmth, cover sleep/wake, manual Wi-Fi state, official Kobo Remote reconnect,
page-turn responsiveness, and battery drain.

