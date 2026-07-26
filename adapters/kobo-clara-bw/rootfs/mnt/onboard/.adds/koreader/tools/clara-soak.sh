#!/bin/sh

# Sample liveness, memory, and battery without keeping any file open on the
# exported onboard filesystem. Copy /tmp/clara-soak.log after the run if needed.
set -u

DURATION_SECONDS="${1:-43200}"
INTERVAL_SECONDS="${2:-60}"
OUTPUT_FILE="${3:-/tmp/clara-soak.log}"
HEALTH_SCRIPT="/mnt/onboard/.adds/koreader/tools/clara-health.sh"

case "${DURATION_SECONDS}:${INTERVAL_SECONDS}" in
    *[!0-9:]*|:*|*:)
        printf 'duration and interval must be positive integers\n' >&2
        exit 2
        ;;
esac
if [ "${DURATION_SECONDS}" -lt 1 ] || [ "${INTERVAL_SECONDS}" -lt 1 ]; then
    printf 'duration and interval must be positive integers\n' >&2
    exit 2
fi

started="$(date '+%s')"
deadline=$((started + DURATION_SECONDS))
failures=0
samples=0

printf 'soak_start=%s duration_seconds=%s interval_seconds=%s\n' \
    "$(date '+%Y-%m-%dT%H:%M:%S%z')" "${DURATION_SECONDS}" "${INTERVAL_SECONDS}" >"${OUTPUT_FILE}"

while :; do
    now="$(date '+%s')"
    samples=$((samples + 1))
    if "${HEALTH_SCRIPT}" >>"${OUTPUT_FILE}" 2>&1; then
        printf 'sample=%s result=pass\n\n' "${samples}" >>"${OUTPUT_FILE}"
    else
        failures=$((failures + 1))
        printf 'sample=%s result=fail failures=%s\n\n' "${samples}" "${failures}" >>"${OUTPUT_FILE}"
    fi
    [ "${now}" -ge "${deadline}" ] && break
    sleep "${INTERVAL_SECONDS}"
done

printf 'soak_end=%s samples=%s failures=%s\n' \
    "$(date '+%Y-%m-%dT%H:%M:%S%z')" "${samples}" "${failures}" >>"${OUTPUT_FILE}"
[ "${failures}" -eq 0 ]
