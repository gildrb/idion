# Add a device adapter

## Status gate

Device manifests declare their evidence level. `verified` adapters may mutate a
mounted reader after the normal detection and verified-backup gates. Adapters
marked `unverified` use the shared mechanics but have not been tested on
physical hardware. `apply`, `setup`, and direct staging refuse them unless the
operator passes `--allow-unverified`. `plan` remains read-only and does not
require the flag.

Blocked devices support detection and backup only. In particular, Kindle
requires a jailbreak plus a KUAL/MRPI adapter; this project will not send a
Kobo `KoboRoot.tgz` to it.

Copy `adapters/_template/device.toml` into `adapters/<device-id>/device.toml`
and give the adapter a unique ID. Keep its profiles, README, and any model
specific rootfs in that same directory.

## Define before coding

1. Add read-only markers that identify one model without relying on its volume
   label.
2. Document the vendor boot chain and smallest required proprietary component.
3. Define cable recovery and a storage-visible disable marker.
4. Record the real SSH account home from the device account database.

Shared Kobo platform files belong in `adapters/_kobo-common/`. Put only
model-specific files in the adapter directory.

## Implement after recovery exists

1. Add bounded, fail-open autostart with a crash counter.
2. Preserve manual Wi-Fi state and generate one host key per device.
3. Add unit tests for every filesystem mutation and archive boundary.
4. Run the remote validator on real hardware.
5. Record display, light, cover, remote, performance, and battery observations.

## Support states

- `verified`: the adapter has passed remote checks and physical tests on named
  hardware and firmware.
- `unverified`: the adapter uses implemented mechanics but has no physical
  hardware test evidence.
- `blocked`: installation is not available for the platform.

To promote an `unverified` adapter to `verified`, run the remote validator on
the named hardware and firmware, then record successful boot, recovery,
display, controls, storage, battery, and repeated-soak tests. The evidence
must be reviewed and the adapter status changed only after those tests pass.
