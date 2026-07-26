#!/bin/sh

# Launch KOReader once per normal boot, after Nickel has initialized the Kobo
# hardware. Recovery is deliberately fail-open: boot with a USB/power cable,
# create the disable marker, or let two early failures trip the circuit breaker.

TAG="koreader-autostart"
ONBOARD="${KO_AUTOSTART_ONBOARD:-/mnt/onboard}"
STATE_DIR="${ONBOARD}/.kobo"
KOREADER="${ONBOARD}/.adds/koreader/koreader.sh"
LUAJIT="${KO_AUTOSTART_LUAJIT:-${ONBOARD}/.adds/koreader/luajit}"
SETTINGS="${ONBOARD}/.adds/koreader/settings.reader.lua"
SETTINGS_PENDING="${SETTINGS}.pending"
SETTINGS_BACKUP="${SETTINGS}.previous"
SETTINGS_REJECTED="${SETTINGS}.rejected"
DISABLE_MARKER="${STATE_DIR}/KOReader-autostart-disabled"
PENDING_MARKER="${STATE_DIR}/KOReader-autostart.pending"
FAILURE_FILE="${STATE_DIR}/KOReader-autostart.failures"
PROC_MOUNTS="${KO_AUTOSTART_PROC_MOUNTS:-/proc/mounts}"
SYS_ROOT="${KO_AUTOSTART_SYS_ROOT:-/sys}"
PIDOF_COMMAND="${KO_AUTOSTART_PIDOF:-pidof}"
LOGGER_COMMAND="${KO_AUTOSTART_LOGGER:-logger}"
RUNTIME_LOG="${KO_AUTOSTART_RUNTIME_LOG:-/tmp/koreader-autostart.log}"
MAX_FAILURES="${KO_AUTOSTART_MAX_FAILURES:-2}"
STARTUP_WAIT_SECONDS="${KO_AUTOSTART_STARTUP_WAIT_SECONDS:-90}"
NICKEL_SETTLE_SECONDS="${KO_AUTOSTART_NICKEL_SETTLE_SECONDS:-8}"
STABLE_SECONDS="${KO_AUTOSTART_STABLE_SECONDS:-60}"

log_message() {
    "${LOGGER_COMMAND}" -t "${TAG}" -- "$*"
    printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" >>"${RUNTIME_LOG}"
}

read_failure_count() {
    count=0
    if [ -r "${FAILURE_FILE}" ]; then
        IFS= read -r count <"${FAILURE_FILE}"
    fi
    case "${count}" in
        ''|*[!0-9]*) count=0 ;;
    esac
    printf '%s\n' "${count}"
}

write_failure_count() {
    temporary_file="${FAILURE_FILE}.new"
    printf '%s\n' "$1" >"${temporary_file}" && mv -f "${temporary_file}" "${FAILURE_FILE}"
}

apply_pending_settings() {
    [ -e "${SETTINGS_PENDING}" ] || return 0

    compiled_settings="/tmp/koreader-settings.$$.luac"
    if [ ! -x "${LUAJIT}" ] || ! "${LUAJIT}" -b "${SETTINGS_PENDING}" "${compiled_settings}"; then
        rm -f "${compiled_settings}"
        mv -f "${SETTINGS_PENDING}" "${SETTINGS_REJECTED}"
        log_message "Rejected invalid staged KOReader settings; keeping the current configuration"
        return 1
    fi
    rm -f "${compiled_settings}"

    if [ -r "${SETTINGS}" ]; then
        if ! cp -p "${SETTINGS}" "${SETTINGS_BACKUP}.new" \
            || ! mv -f "${SETTINGS_BACKUP}.new" "${SETTINGS_BACKUP}"; then
            rm -f "${SETTINGS_BACKUP}.new"
            log_message "Could not back up current KOReader settings; leaving staged settings unapplied"
            return 1
        fi
    fi

    if ! mv -f "${SETTINGS_PENDING}" "${SETTINGS}"; then
        log_message "Could not activate staged KOReader settings; keeping the current configuration"
        return 1
    fi

    rm -f "${PENDING_MARKER}" "${FAILURE_FILE}"
    sync
    log_message "Validated and activated staged KOReader settings"
    return 0
}

# rcS launches the boot animator before Nickel. Wait for both the onboard
# filesystem and Nickel, but never hold an open descriptor on onboard.
seconds_waited=0
while [ "${seconds_waited}" -lt "${STARTUP_WAIT_SECONDS}" ]; do
    if awk -v onboard="${ONBOARD}" '$2 == onboard { found = 1 } END { exit !found }' "${PROC_MOUNTS}" \
        && "${PIDOF_COMMAND}" nickel >/dev/null 2>&1; then
        break
    fi
    sleep 1
    seconds_waited=$((seconds_waited + 1))
done

if [ "${seconds_waited}" -ge "${STARTUP_WAIT_SECONDS}" ]; then
    log_message "Nickel or onboard storage did not become ready; staying in Nickel"
    exit 0
fi

# Let Nickel finish its first screen and hardware pass before KOReader asks it
# to stop. This avoids two display owners racing during boot.
sleep "${NICKEL_SETTLE_SECONDS}"

if [ -e "${DISABLE_MARKER}" ]; then
    log_message "Disable marker present; staying in Nickel"
    exit 0
fi

if [ ! -x "${KOREADER}" ] || [ ! -x "${ONBOARD}/.adds/koreader/reader.lua" ]; then
    log_message "KOReader installation is incomplete; staying in Nickel"
    exit 0
fi

# A cable at boot is the physical recovery path. Both USB hosts and wall
# chargers report Charging/Full through one of these battery devices on Kobo
# platforms. A currently configured USB gadget is checked separately.
for status_file in \
    "${SYS_ROOT}/class/power_supply/battery/status" \
    "${SYS_ROOT}/class/power_supply/bd71827_bat/status" \
    "${SYS_ROOT}/class/power_supply/mc13892_bat/status"
do
    if [ -r "${status_file}" ]; then
        IFS= read -r power_status <"${status_file}"
        case "${power_status}" in
            Charging|Full)
                log_message "External power detected at boot; staying in Nickel for recovery"
                exit 0
                ;;
        esac
    fi
done

if [ -r "${SYS_ROOT}/kernel/config/usb_gadget/g1/UDC" ]; then
    IFS= read -r usb_controller <"${SYS_ROOT}/kernel/config/usb_gadget/g1/UDC"
    if [ -n "${usb_controller}" ]; then
        log_message "USB mass storage is active; staying in Nickel"
        exit 0
    fi
fi

# Remote configuration changes are staged under a separate filename. Validate
# and atomically activate them only during a normal cable-free boot, before
# KOReader can read or rewrite its settings. A bad file is rejected and the
# last known-good configuration remains active.
apply_pending_settings || true

failure_count="$(read_failure_count)"
if [ -e "${PENDING_MARKER}" ]; then
    rm -f "${PENDING_MARKER}"
    failure_count=$((failure_count + 1))
    write_failure_count "${failure_count}"
    log_message "Previous KOReader start did not reach the stability window (${failure_count}/${MAX_FAILURES})"
fi

if [ "${failure_count}" -ge "${MAX_FAILURES}" ]; then
    log_message "Circuit breaker open after ${failure_count} early failures; staying in Nickel"
    exit 0
fi

printf '%s\n' "$(date '+%s')" >"${PENDING_MARKER}"
log_message "Launching KOReader after stable Nickel initialization"

cd /
"${KOREADER}" &
koreader_pid=$!

sleep "${STABLE_SECONDS}"
if kill -0 "${koreader_pid}" >/dev/null 2>&1; then
    rm -f "${PENDING_MARKER}" "${FAILURE_FILE}"
    log_message "KOReader passed the ${STABLE_SECONDS}-second stability window"
    wait "${koreader_pid}"
    exit_code=$?
    log_message "KOReader exited with status ${exit_code}; Nickel recovery remains available"
    exit 0
fi

wait "${koreader_pid}"
exit_code=$?
rm -f "${PENDING_MARKER}"
failure_count=$((failure_count + 1))
write_failure_count "${failure_count}"
log_message "KOReader exited early with status ${exit_code} (${failure_count}/${MAX_FAILURES}); staying in Nickel"
exit 0
