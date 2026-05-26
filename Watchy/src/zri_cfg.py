# ZRI Device Configuration -- Watchy V3
# Haptic timings, tilt settings, button mapping.
# Edit values below, save, and reboot watch to apply.

config = {
    'device': 'watchy',              # Hardware target
    'short_ms': 120,                 # Short buzz duration (dot)
    'long_ms': 380,                  # Long buzz duration (dash)
    'tick_ms': 80,                   # Tick pulse duration (tilt counting)
    'gap_ms': 200,                   # Pause between buzzes in a pattern
    'digit_gap_ms': 650,             # Pause between digits
    'move_gap_ms': 1100,             # Pause between tilt moves
    'tilt_axis': 'x',                # Accelerometer axis for tilt input (x=up/down, y=side-to-side)
    'tilt_invert': False,            # Reverse tilt direction
    'tilt_threshold': 300,           # Accel delta to register a tilt
    'tick_interval_ms': 800,         # Interval between counting ticks
    'confirm_btn': 'TL',             # Button to confirm selection
    'default_centre': 5,             # Starting digit for tilt input (0-9)
}
