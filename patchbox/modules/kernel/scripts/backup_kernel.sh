#!/bin/sh

current_version=$(uname -r | grep -oe [0-9]*\\.[0-9]*\\.[0-9]*)

echo Backing up kernel $current_version...
mkdir -p /boot/backup
for i in $(ls /boot/ | grep -e "kernel.*img\$"); do
	cp -vp /boot/$i /boot/backup/$i
done

echo Backing up device tree...
cp -rpv /boot/*.dtb /boot/overlays /boot/backup/

echo Backing up $current_version modules...
rm -rf /root/.kernel_backup
mkdir -p /root/.kernel_backup
for i in $(ls /lib/modules/ | grep $current_version); do
	echo $i...
	cp -rp /lib/modules/$i /root/.kernel_backup
done
