#!/bin/sh

USER="$1"
if [ -z "$USER" ]; then
    echo "USER variable is missing! Don't execute this script directly!"
    exit 1
fi

echo 'Setting boot environment to Desktop GUI, automatically logged in as "'$USER'" user'

if [ -e /etc/init.d/lightdm ]; then
    systemctl set-default graphical.target
    ln -fs /lib/systemd/system/getty@.service /etc/systemd/system/getty.target.wants/getty@tty1.service
    cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $USER --noclear %I \$TERM
EOF
    sed /etc/lightdm/lightdm.conf -i -e "s/^\(#\|\)autologin-user=.*/autologin-user=$USER/"
else
    whiptail --msgbox "Do 'sudo apt-get install lightdm' to allow configuration of boot to desktop" 20 60 2
    return 1
fi

echo 'Done!'