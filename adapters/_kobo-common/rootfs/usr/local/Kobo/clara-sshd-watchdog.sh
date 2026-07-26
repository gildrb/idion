#!/bin/sh

# Keep the independently started OpenSSH daemon available without touching
# Wi-Fi state or holding any descriptor on /mnt/onboard. This is intentionally
# separate from KOReader and its boot manager.

TAG="clara-sshd-watchdog"
RUNTIME_LOG="${CLARA_SSHD_WATCHDOG_LOG:-/tmp/clara-sshd-watchdog.log}"
CHECK_INTERVAL_SECONDS="${CLARA_SSHD_WATCHDOG_INTERVAL:-30}"
PIDOF_COMMAND="${CLARA_SSHD_PIDOF:-pidof}"
SSHD_COMMAND="${CLARA_SSHD_COMMAND:-/usr/sbin/sshd}"
LOGGER_COMMAND="${CLARA_SSHD_LOGGER:-logger}"

log_message() {
    "${LOGGER_COMMAND}" -t "${TAG}" -- "$*"
    printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" >>"${RUNTIME_LOG}"
}

while :; do
    if ! "${PIDOF_COMMAND}" sshd >/dev/null 2>&1; then
        log_message "sshd is not running; attempting restart"
        if "${SSHD_COMMAND}"; then
            log_message "sshd restarted successfully"
        else
            log_message "sshd restart failed; will retry"
        fi
    fi
    if [ "${CLARA_SSHD_WATCHDOG_ONCE:-false}" = true ]; then
        exit 0
    fi
    sleep "${CHECK_INTERVAL_SECONDS}"
done
