import os

path = os.path.dirname(os.path.realpath(__file__))

# Pisound Server
CFG_SCRIPTS_DIR = os.environ.get("CFG_SCRIPTS_DIR", path + '/scripts/')

# Pisound Button
BTN_SCRIPTS_DIR = os.environ.get("BTN_SCRIPTS", '/usr/local/pisound/scripts/pisound-btn')
BTN_CFG = os.environ.get("BTN_CFG", '/etc/pisound.conf')

# Patchbox Modules
PATCHBOX_MODULE_FOLDER = '/usr/local/patchbox-modules/'
PATCHBOX_MODULE_TMP_FOLDER = '/var/patchbox/tmp/'
PATCHBOX_MODULE_IGNORED = ['system', 'tmp', 'imported']
PATCHBOX_MODULE_FILE = 'patchbox-module.json'
PATCHBOX_MODULE_REQUIRED_KEYS = ['name', 'description', 'version', 'author']

PATCHBOX_STATE_DIR = '/var/patchbox/'
PATCHBOX_STATE_FILE = 'state.json'
