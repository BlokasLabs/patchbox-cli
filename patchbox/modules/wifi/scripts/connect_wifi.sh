#!/bin/bash
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../scripts/import_raspi_config.sh"
do_wifi_ssid_passphrase $@
