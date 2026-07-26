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

## Network state

Wi-Fi state belongs to the reader. No adapter may turn Wi-Fi on, turn it off,
or start an unrelated action because the user changed it. A reader with Wi-Fi
off is deliberately unreachable.

## Report a problem

Send security-sensitive reports privately to the repository owner. Do not
attach installers, backups, runtime evidence, or key material.

