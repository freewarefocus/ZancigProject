# Tilt Trainer Configuration
# Edit values below, save, and reboot watch to apply.
# If this file has errors, defaults are used silently.

config = {

    # Tilt direction
    # 'x' = forward/back (top-to-bottom tilt)
    # 'y' = side-to-side tilt
    'tilt_axis': 'x',

    # Set True to reverse which way tilt counts up/down
    'tilt_invert': False,

    # Haptic pulse timing (milliseconds)
    'short_ms': 35,         # short pulse (shown as * in codes)
    'long_ms': 80,          # long pulse (shown as - in codes)
    'gap_ms': 300,          # pause between pulses

    # Jog dial feel
    'tick_ms': 35,          # buzz when tilt counts up/down
    'tick_interval_ms': 500,# speed of counting (lower = faster)
    'tilt_threshold': 300,  # sensitivity (lower = more sensitive)

    # Number range (any span within 0-9)
    'range_lo': 1,
    'range_hi': 9,

    # Base number -- the dividing line in haptic encoding.
    # Numbers below base: short pulses only (* = 1, ** = 2, etc.)
    # Base number itself: 1 long pulses (-)
    # Numbers above base: long + shorts (-* = base+1, -** = base+2)
    #
    # Example with range 1-6, base 3:
    #   1 = *       2 = **      3 = -
    #   4 = -*     5 = -**    6 = -***
    #
    # Tip: set base at your most common target number for
    # quick recognition. The long pulses feel clearly different
    # from short ones, so crossing the base is unmistakable.
    'base': 5,
}
