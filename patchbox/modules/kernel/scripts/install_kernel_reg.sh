#!/bin/sh

apt update
apt install --reinstall --yes raspberrypi-kernel

echo "Reboot to activate the new kernel version. (run \`sudo reboot\`)"
