#!/bin/sh

# Start the fail-open KOReader session manager from the root filesystem.
# It never redirects output to /mnt/onboard and deliberately waits until
# Nickel has finished hardware initialization before launching KOReader.
/usr/local/Kobo/koreader-autostart.sh &

PRODUCT=$(/bin/sh /bin/kobo_config.sh)
PREFIX=""
[ "${PRODUCT}" != trilogy ] && PREFIX="${PRODUCT}-"
COLOR=$(ntx_hwconfig -S 1 -p /dev/mmcblk0p6 EPD_Flags CFA)

i=0
PARTIAL_UPDATE=0
while :; do
    i=$(((i + 1) % 11))
    image="/etc/images/${PREFIX}on-${i}.raw.gz"
    if [ -s "${image}" ]; then
        if [ "${COLOR}" = "ON" ]; then
            zcat "${image}" | /usr/local/Kobo/pickel showpic "${PARTIAL_UPDATE}"
            PARTIAL_UPDATE=1
        else
            zcat "${image}" | /usr/local/Kobo/pickel showpic 1
        fi
        usleep 250000
    fi
done
