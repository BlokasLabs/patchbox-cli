#!/bin/sh

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install --reinstall --yes linux-image-rpi-rt-v6 linux-image-rpi-rt-v7 linux-image-rpi-rt-v7l linux-image-rpi-rt-v8 linux-image-rpi-rt-2712

echo "Reboot to activate the new kernel version. (run \`sudo reboot\`)"
