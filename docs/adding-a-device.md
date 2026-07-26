# Add a device adapter

## Status gate

Device manifests declare their evidence level. `hardware-beta` adapters may
mutate a mounted reader after the normal detection and verified-backup gates.
Adapters marked `staging-beta` are intentionally untested on physical hardware:
`apply`, `setup`, and direct staging refuse them unless the operator passes
`--allow-untested`. `plan` remains read-only and does not require the flag.

Non-Kobo devices are detection and backup scaffolds until their vendor boot
mechanism is implemented. In particular, Kindle requires a jailbreak plus a
KUAL/MRPI adapter; this project will not send a Kobo `KoboRoot.tgz` to it.

Copy `devices/_template.toml` and give the adapter a unique ID.

## Define before coding

1. Add read-only markers that identify one model without relying on its volume
   label.
2. Document the vendor boot chain and smallest required proprietary component.
3. Define cable recovery and a storage-visible disable marker.
4. Record the real SSH account home from the device account database.

## Implement after recovery exists

1. Add bounded, fail-open autostart with a crash counter.
2. Preserve manual Wi-Fi state and generate one host key per device.
3. Add unit tests for every filesystem mutation and archive boundary.
4. Run the remote validator on real hardware.
5. Record display, light, cover, remote, performance, and battery observations.

## Support states

- `scaffold`: metadata only; installation is blocked.
- `hardware-beta`: remote tests pass on named firmware and hardware.
- `production`: remote and physical gates pass across repeated boots and soak.

Promoting one state normally takes 30–60 minutes for remote checks plus at
least one overnight battery soak.

Next: make detection fail when the model marker is missing.
