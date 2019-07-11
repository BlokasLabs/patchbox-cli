#!/bin/sh

USER="$1"
if [ -z "$USER" ]; then
    echo "USER variable is missing! Don't execute this script directly!"
    exit 1
fi

echo 'Setting boot environment to Desktop GUI, requiring user "'$USER'" to login'

if [ -e /etc/init.d/lightdm ]; then
    systemctl set-default graphical.target
    ln -fs /lib/systemd/system/getty@.service /etc/systemd/system/getty.target.wants/getty@tty1.service
    rm -f /etc/systemd/system/getty@tty1.service.d/autologin.conf
    sed /etc/lightdm/lightdm.conf -i -e "s/^autologin-user=.*/#autologin-user=/"
else
    echo "Do 'sudo apt-get install lightdm' to allow configuration of boot to desktop"
    return 1
fi

echo 'Done!'