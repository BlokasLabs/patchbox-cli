#!/bin/sh

USER=${SUDO_USER:-$(who -m | awk '{ print $1 }')}

if [ "$1" = "autologin" ]; then
	systemctl set-default multi-user.target
	ln -fs /lib/systemd/system/getty@.service /etc/systemd/system/getty.target.wants/getty@tty1.service
	cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $USER --noclear %I \$TERM
EOF
else
	systemctl set-default multi-user.target
	ln -fs /lib/systemd/system/getty@.service /etc/systemd/system/getty.target.wants/getty@tty1.service
	rm -f /etc/systemd/system/getty@tty1.service.d/autologin.conf
fi
