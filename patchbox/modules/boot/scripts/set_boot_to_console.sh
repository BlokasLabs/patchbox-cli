#!/bin/bash

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../scripts/import_raspi_config.sh"

if [ "$1" != "autologin" ]; then
	BOOTOPT="B1"
else
	BOOTOPT="B2"
fi

do_boot_behaviour $BOOTOPT
echo OK
