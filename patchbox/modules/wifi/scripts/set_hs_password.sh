#!/bin/sh
exec nmcli c mod pb-hotspot wifi-sec.psk "$@"
