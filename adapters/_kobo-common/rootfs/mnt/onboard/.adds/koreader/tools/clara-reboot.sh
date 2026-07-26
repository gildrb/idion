#!/bin/sh

# Flush reading state and reboot through the kernel. The fail-open autostart
# manager will return to KOReader after Nickel initializes the hardware.
sync
exec /sbin/reboot
