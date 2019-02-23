#!/bin/sh

systemctl set-default multi-user.target
ln -fs /lib/systemd/system/getty@.service /etc/systemd/system/getty.target.wants/getty@tty1.service
rm /etc/systemd/system/getty@tty1.service.d/autologin.conf
