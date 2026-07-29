# Architecture

Put portable behavior in `src/koreader_appliance` and hardware behavior in one
directory per adapter under `adapters/`. Shared Kobo platform files belong in
`adapters/_kobo-common/`.

```text
CLI
 ├─ registry and detection
 ├─ verified storage backup
 ├─ transactional bundle staging and rollback tree
 ├─ declarative appliance state planning and apply
 ├─ generated keys and root-package builder
 ├─ document profiles
 └─ evidence collection
      ↓
device adapter
 ├─ identity markers
 ├─ mount layout
 ├─ launch mode and onboard overlay
 ├─ recovery markers
 ├─ SSH account paths
 └─ physical acceptance gates
```

## Portable core

The core may detect storage markers, hash files, reject archive traversal,
stage a complete replacement tree, preserve declared mutable state, generate
keys, render SSH profiles, and modify a closed document sidecar. It must not
assume a vendor boot hook or display driver.

## Device adapter

An adapter owns boot timing, hardware initialization, autostart failure rules,
recovery markers, account-home paths, and physical acceptance gates. Adapter
status records whether those paths have been tested on hardware. The Clara BW
overlay contains a minimal Bluetooth-only KOReader plugin. Its source and
upstream commit are versioned with the adapter; no paired-device addresses or
runtime settings enter the repository.

## Failure containment

The stable profile keeps Nickel as the boot and hardware owner. KOReader is a
manually launched application, so a KOReader or plugin crash returns to a
working vendor UI. Staging writes `.adds/koreader.staging`, syncs it, preserves
the declared mutable entries, and only then switches directories. The last
tree remains as `.adds/koreader.previous`.

The root package contains NickelMenu and the host policy only. Root SSH,
watchdogs, and KOReader boot hooks are excluded. Key-only diagnostic SSH is
owned by KOReader and disappears when KOReader exits.

## Secret flow

1. The operator supplies one public login key outside the repository.
2. Setup writes it to KOReader's `settings/SSH/authorized_keys`.
3. KOReader starts Dropbear with key-only authentication on port 2222.
4. Private client keys and device-generated host keys never enter the
   repository or appliance manifest.

## Evidence boundary

Remote tests can prove processes, hashes, transfers, watchdog recovery, memory,
storage, and battery telemetry. They cannot prove screen flicker, light color,
cover behavior, button feel, or subjective page-turn latency.
