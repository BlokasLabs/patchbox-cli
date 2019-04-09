import os

path = os.path.dirname(os.path.realpath(__file__))

# Pisound Server
CFG_SCRIPTS_DIR = os.environ.get("CFG_SCRIPTS_DIR", path + '/scripts/')

# Pisound Button
BTN_SCRIPTS_DIR = os.environ.get("BTN_SCRIPTS", '/usr/local/pisound/scripts/pisound-btn')
BTN_CFG = os.environ.get("BTN_CFG", '/etc/pisound.conf')

# Patchbox WiFi / Hotspot
HS_CFG = os.environ.get("HS_CFG", '/etc/hostapd/hostapd.conf')
HS_DNS_CFG = os.environ.get("HS_CFG", '/etc/dnsmasq.d/wifi-hotspot.conf')

# Patchbox Modules
PATCHBOX_MODULE_FOLDER = '/usr/local/patchbox-modules/'
PATCHBOX_MODULE_TMP_FOLDER = '/root/.patchbox/tmp/'
PATCHBOX_MODULE_IGNORED = ['system', 'tmp', 'imported']
PATCHBOX_MODULE_FILE = 'patchbox-module.json'
PATCHBOX_MODULE_REQUIRED_KEYS = ['name', 'description', 'version', 'author']
