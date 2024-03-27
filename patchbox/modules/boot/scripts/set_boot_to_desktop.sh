#!/bin/bash

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../scripts/import_raspi_config.sh"

if [ "$1" != "autologin" ]; then
	BOOTOPT="B3"
else
	BOOTOPT="B4"
fi

do_boot_behaviour $BOOTOPT
echo OK
