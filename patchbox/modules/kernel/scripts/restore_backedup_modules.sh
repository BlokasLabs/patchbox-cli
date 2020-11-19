#!/bin/sh

current_version=$(uname -r | grep -oe [0-9]*\\.[0-9]*\\.[0-9]*)

cp -rp /root/.kernel_backup/$current_version* /lib/modules/
rm -rf /root/.kernel_backup
