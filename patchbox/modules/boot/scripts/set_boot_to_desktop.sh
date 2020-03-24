#!/bin/sh

USER=${SUDO_USER:-$(who -m | awk '{ print $1 }')}

disable_raspi_config_at_boot() {
	if [ -e /etc/profile.d/raspi-config.sh ]; then
		rm -f /etc/profile.d/raspi-config.sh
		if [ -e /etc/systemd/system/getty@tty1.service.d/raspi-config-override.conf ]; then
			rm /etc/systemd/system/getty@tty1.service.d/raspi-config-override.conf
		fi
		telinit q
	fi
}

if [ "$1" = "autologin" ]; then
	if [ -e /etc/init.d/lightdm ]; then
		systemctl set-default graphical.target
		ln -fs /lib/systemd/system/getty@.service /etc/systemd/system/getty.target.wants/getty@tty1.service
		cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $USER --noclear %I \$TERM
EOF
		sed /etc/lightdm/lightdm.conf -i -e "s/^\(#\|\)autologin-user=.*/autologin-user=$USER/"
		disable_raspi_config_at_boot
	else
		echo "Do 'sudo apt-get install lightdm' to allow configuration of boot to desktop"
		return 1
	fi
else
	if [ -e /etc/init.d/lightdm ]; then
		systemctl set-default graphical.target
		ln -fs /lib/systemd/system/getty@.service /etc/systemd/system/getty.target.wants/getty@tty1.service
		rm -f /etc/systemd/system/getty@tty1.service.d/autologin.conf
		sed /etc/lightdm/lightdm.conf -i -e "s/^autologin-user=.*/#autologin-user=/"
		disable_raspi_config_at_boot
	else
		echo "Do 'sudo apt-get install lightdm' to allow configuration of boot to desktop"
		return 1
	fi
fi
