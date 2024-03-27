#!/bin/sh

current_version=$(uname -r | grep -oe [0-9]*\\.[0-9]*\\.[0-9]*)

BACKUP_SRC=/boot/firmware
BACKUP_DST=/boot/firmware/backup
MODULE_BACKUP_DST="$BACKUP_DST/modules"

echo Backing up kernel $current_version...
mkdir -p "$BACKUP_DST"
for i in $(ls "$BACKUP_SRC/" | grep -e "kernel.*img\$"); do
	cp -vp "$BACKUP_SRC/$i" "$BACKUP_DST/$i"
done

echo Backing up device tree...
cp -rpv "$BACKUP_SRC/*.dtb" "$BACKUP_SRC/overlays" "$BACKUP_DST/"

echo Backing up $current_version modules...
rm -rf "$MODULE_BACKUP_DST"
mkdir -p "$MODULE_BACKUP_DST"
for i in $(ls /lib/modules/ | grep $current_version); do
	echo $i...
	cp -rp /lib/modules/$i "$MODULE_BACKUP_DST"
done
