# Security policy

Run a secret scan over the exact staged tree before every push.

## Never commit

1. Device, client, or SSH host private keys.
2. Wi-Fi credentials, serial numbers, IP addresses, or account data.
3. Books, annotations, personal dictionaries, or storage backups.
4. Proprietary firmware, generated installers, or disk images.
5. Runtime evidence or active KOReader settings copied from a real reader.

The CLI generates device credentials inside ignored output directories. It
embeds the host private key only in the selected installer and exports the
public host identity for pinning.

## Required SSH posture

1. Generate a different Ed25519 host key for every reader.
2. Accept only an explicit operator public key.
3. Pin the device host key on the client.
4. Disable passwords, forwarding, tunnels, and connection sharing.
5. Stop temporary passwordless recovery services immediately after repair.

The default NickelMenu appliance does not autostart SSH or any other network
service. KOReader's SSH settings remain key-only and hardened for an operator
who explicitly enables diagnostics. The shipped policy disables every
installed KOReader plugin, including `kobo_remote`, and the rootfs blocks
Nickel analytics, store/sync, and silent OTA upgrade endpoints. The CLI itself
makes no network calls.

## Network state

Wi-Fi state belongs to the reader. No adapter may turn Wi-Fi on, turn it off,
or start an unrelated action because the user changed it. A reader with Wi-Fi
off is deliberately unreachable.

Nickel privacy hardening sets airplane and sideloaded mode and clears the
queued analytics file on every apply. It does not rewrite `KoboReader.sqlite`;
avoiding vendor-database surgery is an intentional stability limitation.

## Report a problem

Send security-sensitive reports privately to the repository owner. Do not
attach installers, backups, runtime evidence, or key material.
