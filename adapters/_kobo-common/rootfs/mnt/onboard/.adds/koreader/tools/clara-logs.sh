#!/bin/sh

# Print the compact evidence set normally needed to diagnose KOReader issues.
printf '%s\n' '===== health ====='
/mnt/onboard/.adds/koreader/tools/clara-health.sh || true

printf '%s\n' '===== autostart ====='
cat /tmp/koreader-autostart.log 2>/dev/null || true

printf '%s\n' '===== SSH watchdog ====='
cat /tmp/clara-sshd-watchdog.log 2>/dev/null || true

printf '%s\n' '===== KOReader crash log ====='
tail -n 300 /mnt/onboard/.adds/koreader/crash.log 2>/dev/null || true

printf '%s\n' '===== system log ====='
logread 2>/dev/null | tail -n 300 || true

printf '%s\n' '===== mounts ====='
mount

printf '%s\n' '===== processes ====='
ps w
