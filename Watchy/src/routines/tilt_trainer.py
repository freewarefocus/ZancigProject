"""
routines/tilt_trainer.py
Configurable jog dial practice using ZRI.
Short press = confirm + haptic echo. Long press = reset to base.

Encoding:
  Numbers below base: short pulses only (counting from 1)
  Base number: 1 long pulse (-)
  Numbers above base: 1 long + short pulses (-*, -**, etc.)
  Zero: 2 longs (--) -- silence is undetectable
"""
import zri


DEFAULTS = {
    'range_lo': 1,
    'range_hi': 9,
    'base': 5,
}


def encode(n, cfg):
    """Return (longs, shorts) for haptic output."""
    if n == 0:
        return 2, 0
    if n < cfg['base']:
        return 0, n - cfg['range_lo'] + 1
    return 1, n - cfg['base']


def code_str(n, cfg):
    """Human-readable code: - for long, * for short."""
    lo, sh = encode(n, cfg)
    return '-' * lo + '*' * sh


def pattern_str(n, cfg):
    """ZRI haptic pattern: L for long, S for short."""
    lo, sh = encode(n, cfg)
    return 'L' * lo + 'S' * sh


def run():
    zri.init()
    cfg = zri.load_config('tilt_trainer', DEFAULTS)
    lo, hi = cfg['range_lo'], cfg['range_hi']

    def format_fn(n):
        return code_str(n, cfg)

    while True:
        n = zri.get_digit(lo, hi, prompt="TILT TRAINER", format_fn=format_fn)
        zri.sleep_ms(300)
        zri.haptic(pattern_str(n, cfg))
        zri.show(["CONFIRMED", str(n), code_str(n, cfg)])
        zri.sleep_ms(1500)
