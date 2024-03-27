#!/bin/bash
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../scripts/import_raspi_config.sh"
get_wifi_country
