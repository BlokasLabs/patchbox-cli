#!/bin/sh

DEBIAN_FRONTEND=noninteractive apt-get update
DEBIAN_FRONTEND=noninteractive apt-get purge --yes blokas-initrd-rt linux-image-rpi-rt-v6 linux-image-rpi-rt-v7 linux-image-rpi-rt-v7l linux-image-rpi-rt-v8 linux-image-rpi-rt-2712
DEBIAN_FRONTEND=noninteractive apt-get install --reinstall --yes linux-image-rpi-v6 linux-image-rpi-v7 linux-image-rpi-v7l linux-image-rpi-v8 linux-image-rpi-2712

echo "Reboot to activate the new kernel version. (run \`sudo reboot\`)"
