"""
routines/tilt_trainer.py
Configurable jog dial practice. Edit /routines/tilt_trainer_cfg.py to tune.
Short press = confirm + haptic echo. Long press = reset to base.

Encoding:
  Numbers below base: short pulses only (counting from 1)
  Base number: 1 long pulse (-)
  Numbers above base: 1 long + short pulses (-*, -**, etc.)
  Zero: 2 longs (--) -- silence is undetectable
"""
import zancig
import time


DEFAULTS = {
    'tilt_axis': 'y',       # 'x'=forward/back, 'y'=side-to-side
    'tilt_invert': False,   # flip tilt direction
    'short_ms': 120,        # short pulse duration
    'long_ms': 380,         # long pulse duration
    'gap_ms': 200,          # gap between pulses
    'tick_ms': 80,          # tick pulse when tilt counts
    'tick_interval_ms': 800,# ms between tilt increments
    'tilt_threshold': 300,  # accel delta to register tilt
    'range_lo': 1,          # lowest number (0-9)
    'range_hi': 9,          # highest number (0-9)
    'base': 5,              # divider: below=shorts, at/above=longs+shorts
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


def send_value(n, cfg):
    """Play haptic encoding for number n."""
    lo, sh = encode(n, cfg)
    for i in range(lo):
        zancig.buzz(cfg['long_ms'],
                    cfg['gap_ms'] if (sh > 0 or i < lo - 1) else 0)
    for i in range(sh):
        zancig.buzz(cfg['short_ms'],
                    cfg['gap_ms'] if i < sh - 1 else 0)


def get_delta(neutral, cfg):
    """Tilt delta using configured axis and direction."""
    nx, ny, nz = neutral
    x, y, z = zancig.accel_xyz()
    d = (x - nx) if cfg['tilt_axis'] == 'x' else (y - ny)
    return -d if cfg['tilt_invert'] else d


def draw_main(current, cfg):
    """Main trainer screen: title, big digit, code, range info."""
    zancig.display_clear()
    zancig.display_text("TILT TRAINER", 5, 2)
    zancig.display_rect(0, 20, 200, 1)
    zancig.display_big_digit(current, 52, 28)
    code = code_str(current, cfg)
    zancig.display_text(code, (200 - len(code) * 16) // 2, 135)
    lo, hi, b = cfg['range_lo'], cfg['range_hi'], cfg['base']
    zancig.display_text(f"{lo}-{hi} base:{b}", 5, 185, scale=1)
    zancig.display_show()


def draw_confirmed(current, cfg):
    """Confirmation screen after short press."""
    zancig.display_clear()
    zancig.display_text("CONFIRMED", 20, 2)
    zancig.display_big_digit(current, 52, 28)
    code = code_str(current, cfg)
    zancig.display_text(code, (200 - len(code) * 16) // 2, 135)
    zancig.display_show()


def run():
    cfg = zancig.load_config('tilt_trainer', DEFAULTS)

    draw_main(cfg['base'], cfg)

    neutral = zancig.calibrate_neutral()
    current = cfg['base']
    last_displayed = -1
    last_tick_t = time.ticks_ms()
    lo, hi = cfg['range_lo'], cfg['range_hi']

    while True:
        if current != last_displayed:
            draw_main(current, cfg)
            last_displayed = current

        delta = get_delta(neutral, cfg)
        now = time.ticks_ms()

        if time.ticks_diff(now, last_tick_t) >= cfg['tick_interval_ms']:
            if delta > cfg['tilt_threshold'] and current > lo:
                current -= 1
                zancig.buzz(cfg['tick_ms'], cfg['gap_ms'])
                last_tick_t = now
            elif delta < -cfg['tilt_threshold'] and current < hi:
                current += 1
                zancig.buzz(cfg['tick_ms'], cfg['gap_ms'])
                last_tick_t = now

        press = zancig.check_button('TL')
        if press == 'short':
            time.sleep_ms(300)
            send_value(current, cfg)
            draw_confirmed(current, cfg)
            time.sleep_ms(1500)
            current = cfg['base']
            last_displayed = -1

        elif press == 'long':
            zancig.send_nack()
            current = cfg['base']
            last_displayed = -1

        if zancig.check_button('BL'):
            return

        time.sleep_ms(20)
