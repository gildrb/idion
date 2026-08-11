# Kobo Clara BW adapter

Start with `idion backup`; do not build or stage an installer
until the backup finishes and its hashes match.

## Observed behavior

1. Firmware `4.45.23697` on product `P365` starts KOReader after bounded Nickel
   hardware initialization.
2. A cable at boot or `.kobo/KOReader-autostart-disabled` keeps the device in
   Nickel for recovery.
3. Two early KOReader failures open the launch circuit instead of creating an
   endless crash loop.
4. The default NickelMenu path starts no network service. KOReader SSH remains
   key-only and hardened if an operator explicitly enables it.
5. Autostart builds, when deliberately selected, require explicitly supplied
   ARM `sftp-server`, `scp`, and static `rsync` binaries whose hashes are
   recorded in the generated build manifest. NickelMenu builds do not require
   these root-SSH inputs.

## Required local inputs

1. An official KOReader Kobo archive.
2. One operator public key and the ARM transfer binaries when using autostart.
3. A NickelMenu KoboRoot package when using NickelMenu mode.
4. A mounted Clara BW that matches the P365 detection marker.

Firmware, private keys, books, and generated installers stay outside Git.

The shipped rootfs blackholes Nickel analytics, store/sync, and silent OTA
upgrade endpoints while leaving `www.kobo.com` reachable for captive-portal
detection. The appliance clears Nickel's queued analytics events, enables
airplane and sideloaded mode, and disables every installed KOReader plugin,
including `kobo_remote`. It deliberately does not modify `KoboReader.sqlite`;
that vendor database is a documented privacy limitation and stability tradeoff.

## Physical acceptance

The automated validator cannot see the e-ink panel or operate the cover. A
release still requires observed display stability, ComfortLight intensity and
warmth, cover sleep/wake, manual Wi-Fi state, official Kobo Remote reconnect,
page-turn responsiveness, and battery drain.
