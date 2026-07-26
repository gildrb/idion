# Architecture

Put portable behavior in `src/koreader_appliance` and hardware behavior in one
directory per adapter under `adapters/`. Shared Kobo platform files belong in
`adapters/_kobo-common/`.

```text
CLI
 ├─ registry and detection
 ├─ verified storage backup
 ├─ safe bundle staging
 ├─ declarative appliance state planning and apply
 ├─ generated keys and root-package builder
 ├─ document profiles
 └─ evidence collection
      ↓
device adapter
 ├─ identity markers
 ├─ mount layout
 ├─ boot and activation mechanism
 ├─ recovery markers
 ├─ SSH account paths
 └─ physical acceptance gates
```

## Portable core

The core may detect storage markers, hash files, reject archive traversal,
stage additive content, generate keys, render SSH profiles, and modify a closed
document sidecar. It must not assume a vendor boot hook or display driver.

## Device adapter

An adapter owns boot timing, hardware initialization, autostart failure rules,
recovery markers, account-home paths, and physical acceptance gates. Adapter
status records whether those paths have been tested on hardware.

## Secret flow

1. The operator supplies one public login key.
2. The builder creates a host key in a temporary directory.
3. The private host key enters only the ignored installer output.
4. The public host key and fingerprint remain available for client pinning.

## Evidence boundary

Remote tests can prove processes, hashes, transfers, watchdog recovery, memory,
storage, and battery telemetry. They cannot prove screen flicker, light color,
cover behavior, button feel, or subjective page-turn latency.
