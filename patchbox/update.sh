#!/bin/sh
SOFTWARE_TO_INSTALL="pisound-btn pisound-ctl amidiauto patchbox-cli"
sudo apt-get update
sudo apt-get install $SOFTWARE_TO_INSTALL -y
cd /usr/local/patchbox-cli && git pull
cd /usr/local/patchbox-modules && git pull
