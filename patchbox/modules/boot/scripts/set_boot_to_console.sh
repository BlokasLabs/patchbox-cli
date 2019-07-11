#!/bin/sh

USER="$1"
if [ -z "$USER" ]; then
    echo "USER variable is missing! Don't execute this script directly!"
    exit 1
fi

echo 'Setting boot environment to Console, requiring user "'$USER'" to login'

systemctl set-default multi-user.target
ln -fs /lib/systemd/system/getty@.service /etc/systemd/system/getty.target.wants/getty@tty1.service
rm -f /etc/systemd/system/getty@tty1.service.d/autologin.conf

echo 'Done!'