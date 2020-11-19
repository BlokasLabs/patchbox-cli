#!/bin/sh

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

apt update
$SCRIPT_DIR/backup_kernel.sh
apt install --reinstall --yes raspberrypi-kernel-rt
$SCRIPT_DIR/restore_backedup_modules.sh

echo "Reboot to activate the new kernel version. (run \`sudo reboot\`)"
