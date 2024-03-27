#!/bin/bash

# Workaround exit being used to terminate `/usr/bin/raspi-config`.
exit() { return 0; }

# Import functions like `is_wayland`, `get_wifi_country`, etc...
source /usr/bin/raspi-config nonint &> /dev/null

# Restore `exit`.
unset -f exit
