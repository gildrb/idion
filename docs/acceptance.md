# Clara BW acceptance protocol

Software checks prove deterministic files and bounded failure behavior. They
cannot prove a physical reader, cover sensor, battery, or Bluetooth radio. A
build earns the `verified` label only after this protocol passes on the named
firmware and hardware.

## Release gates

1. Run the Python test suite and compile check on Python 3.11, 3.12, and 3.13.
2. Verify every downloaded artifact against its manifest SHA-256 digest.
3. Create and verify an off-device backup before staging.
4. Confirm Nickel boots and opens a book before the first KOReader launch.
5. Confirm KOReader opens the same EPUB and PDF after 20 cold boots.
6. Complete 100 cover sleep/wake cycles. No cycle may take more than ten
   seconds, require a forced reboot, or lose the last document position.
7. Complete 100 Bluetooth sleep/wake cycles with the paired Kobo Remote.
   Pairing must persist and input must reconnect without opening a settings
   menu. Record the reconnect time; no cycle may exceed ten seconds.
8. Leave the reader in normal daily use for seven days. Record battery level,
   unexpected exits, failed wakes, and manual Bluetooth interventions.
9. Verify key-only SSH on port 2222, reject password authentication, then
   repeat with Wi-Fi disabled to confirm the service is unreachable.
10. Re-run `plan`; every state item except the consumed root-package trigger
    must be `ok`.

Any failed gate blocks the release. Keep NickelMenu launch mode while
investigating; never use autostart to conceal a failing manual-launch build.

## Recovery drill

With the verified backup disconnected from the reader, copy a disposable test
file to the device, back it up, remove the device copy, and restore it from the
backup. Compare SHA-256 digests. This proves the recovery path without erasing
the reader or performing a factory reset.
