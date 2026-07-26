#!/bin/sh

# Read-only health snapshot for a KOReader-first Clara BW.
set -u

read_first() {
    for path in "$@"; do
        if [ -r "${path}" ]; then
            IFS= read -r value <"${path}"
            printf '%s' "${value}"
            return 0
        fi
    done
    printf 'unavailable'
}

koreader_pid="$(pidof reader.lua 2>/dev/null | awk '{ print $1 }')"
if [ -z "${koreader_pid}" ]; then
    koreader_pid="$(pidof luajit 2>/dev/null | awk '{ print $1 }')"
fi
sshd_watchdog_pid="$(ps w 2>/dev/null | awk '/[c]lara-sshd-watchdog\.sh/ { print $1 }' | tr '\n' ',' | sed 's/,$//')"

printf 'timestamp=%s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')"
printf 'hostname=%s\n' "$(hostname 2>/dev/null || printf unknown)"
printf 'uptime_seconds=%s\n' "$(cut -d. -f1 /proc/uptime 2>/dev/null || printf unavailable)"
printf 'load_average=%s\n' "$(cat /proc/loadavg 2>/dev/null || printf unavailable)"
printf 'memory_available_kib=%s\n' "$(awk '/^MemAvailable:/ { print $2 }' /proc/meminfo 2>/dev/null)"
printf 'battery_percent=%s\n' "$(read_first /sys/class/power_supply/*/capacity)"
printf 'battery_status=%s\n' "$(read_first /sys/class/power_supply/*/status)"
printf 'battery_temperature=%s\n' "$(read_first /sys/class/power_supply/*/temp /sys/class/thermal/thermal_zone*/temp)"
printf 'framebuffer_bpp=%s\n' "$(read_first /sys/class/graphics/fb0/bits_per_pixel)"
printf 'framebuffer_rotation=%s\n' "$(read_first /sys/class/graphics/fb0/rotate)"
printf 'koreader_pid=%s\n' "${koreader_pid:-missing}"
printf 'nickel_pid=%s\n' "$(pidof nickel 2>/dev/null || printf stopped)"
printf 'sshd_pid=%s\n' "$(pidof sshd 2>/dev/null || printf stopped)"
printf 'sshd_watchdog_pid=%s\n' "${sshd_watchdog_pid:-stopped}"
printf 'bluetooth_processes=%s\n' "$(pidof bluetoothd mtk_bluetoothd 2>/dev/null || printf stopped)"
printf 'wifi_interface=%s\n' "$(awk '$1 ~ /^(wlan0|eth0|mlan0):/ { sub(":", "", $1); print $1; exit }' /proc/net/dev 2>/dev/null || printf off)"
printf 'ipv4_addresses=%s\n' "$(ifconfig 2>/dev/null | awk '/inet addr:/ { sub("addr:", "", $2); printf "%s,", $2 }' | sed 's/,$//' || printf none)"
printf 'autostart_disabled=%s\n' "$([ -e /mnt/onboard/.kobo/KOReader-autostart-disabled ] && printf true || printf false)"
printf 'autostart_pending=%s\n' "$([ -e /mnt/onboard/.kobo/KOReader-autostart.pending ] && printf true || printf false)"
printf 'autostart_failures=%s\n' "$(cat /mnt/onboard/.kobo/KOReader-autostart.failures 2>/dev/null || printf 0)"
printf 'settings_staged=%s\n' "$([ -e /mnt/onboard/.adds/koreader/settings.reader.lua.pending ] && printf true || printf false)"
printf 'settings_rejected=%s\n' "$([ -e /mnt/onboard/.adds/koreader/settings.reader.lua.rejected ] && printf true || printf false)"
printf 'rsync_path=%s\n' "$(command -v rsync 2>/dev/null || printf missing)"
printf 'scp_path=%s\n' "$(command -v scp 2>/dev/null || printf missing)"
printf 'sftp_server=%s\n' "$([ -x /usr/libexec/sftp-server ] && printf /usr/libexec/sftp-server || printf missing)"
printf 'kobo_remote_input=%s\n' "$(awk -F= '/^N: Name=/{ name=$2 } /Kobo Remote|KOBO REMOTE/{ print name; found=1 } END { if (!found) print "disconnected" }' /proc/bus/input/devices 2>/dev/null | tr '\n' ',' | sed 's/,$//')"

if [ -n "${koreader_pid}" ] && [ -r "/proc/${koreader_pid}/status" ]; then
    awk '/^(State|VmPeak|VmSize|VmRSS|VmSwap|Threads):/ { key=$1; sub(":", "", key); print "koreader_" tolower(key) "=" $2 $3 }' "/proc/${koreader_pid}/status"
fi

df -k /mnt/onboard 2>/dev/null | awk 'NR == 2 { print "storage_used_kib=" $3; print "storage_free_kib=" $4 }'

if [ -n "${koreader_pid}" ] \
    && [ -n "${sshd_watchdog_pid}" ] \
    && pidof sshd >/dev/null 2>&1 \
    && command -v rsync >/dev/null 2>&1 \
    && command -v scp >/dev/null 2>&1 \
    && [ -x /usr/libexec/sftp-server ]; then
    exit 0
fi
exit 1
