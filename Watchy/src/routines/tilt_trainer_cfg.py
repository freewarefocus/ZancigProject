# Tilt Trainer Configuration
# Edit values below, save, and reboot watch to apply.
# If this file has errors, defaults are used silently.
#
# Tilt/haptic device settings are now in /zri_cfg.py.
# This file only holds routine-specific settings.

config = {
    # Number range (any span within 0-9)
    'range_lo': 1,
    'range_hi': 9,

    # Base number -- the dividing line in haptic encoding.
    # Numbers below base: short pulses only (* = 1, ** = 2, etc.)
    # Base number itself: 1 long pulse (-)
    # Numbers above base: long + shorts (-* = base+1, -** = base+2)
    #
    # Example with range 1-6, base 3:
    #   1 = *       2 = **      3 = -
    #   4 = -*     5 = -**    6 = -***
    'base': 5,
}
