#!/bin/sh

USER=${SUDO_USER:-$(who -m | awk '{ print $1 }')}
DISPLAY=$(ls /tmp/.X11-unix | head -n 1 | tr 'X' ':')
export XAUTHORITY=/home/$USER/.Xauthority
su -p $USER -c "gtk-launch --display=$DISPLAY patchbox-stop.desktop $@"
