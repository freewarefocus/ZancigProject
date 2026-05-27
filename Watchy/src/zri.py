"""
zri.py -- Zancig Routine Interface (Watchy V3 implementation)
Device-agnostic API for routines. Imports zancig internally.
"""

import zancig
import time

# -- Configuration & Capabilities ---------------------------------------------

_cfg = {}
_neutral = None
_hw_ready = False
_font_scale = 2

CAPS = {}


def init():
    """Prepare ZRI for use. Safe to call multiple times.
    First call: hardware init, load config, populate CAPS.
    Every call: (re)calibrate accelerometer neutral baseline.
    Launcher calls this at boot. Routines call it again at start so the
    neutral position is captured when the performer is ready to go."""
    global _cfg, _neutral, _hw_ready

    if not _hw_ready:
        zancig.init()

        defaults = {
            'device': 'watchy',
            'short_ms': zancig.SHORT_MS,
            'long_ms': zancig.LONG_MS,
            'tick_ms': zancig.TICK_MS,
            'gap_ms': zancig.GAP_MS,
            'digit_gap_ms': zancig.DIGIT_GAP,
            'move_gap_ms': zancig.MOVE_GAP,
            'tilt_axis': 'x',
            'tilt_invert': False,
            'tilt_threshold': zancig.TILT_THRESHOLD,
            'tick_interval_ms': zancig.TICK_INTERVAL_MS,
            'confirm_btn': 'TR',
            'default_centre': 5,
        }

        try:
            ns = {}
            with open('/zri_cfg.py') as f:
                exec(f.read(), ns)
            defaults.update(ns['config'])
        except Exception:
            pass

        _cfg = defaults

        CAPS.update({
            'haptic': True,
            'screen': True,
            'accel': True,
            'battery': True,
            'brightness': False,
            'sound': False,
            'device': _cfg['device'],
            'input_method': 'tilt',
        })

        _hw_ready = True

    _neutral = zancig.calibrate_neutral()


# -- Lifecycle -----------------------------------------------------------------

def stealth():
    """Go dark. Clears display for covert state."""
    if not CAPS.get('screen'):
        return False
    zancig.display_clear()
    zancig.display_show()
    return True


def done(timeout_ms=60_000):
    """Routine is finished. Clears display for stealth, waits for any button
    press or timeout, then returns to the launcher menu.
    On timeout, returns so the launcher can handle its own sleep logic."""
    stealth()
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
        for name in ('TL', 'TR', 'BL', 'BR'):
            if zancig.check_button(name):
                return
        time.sleep_ms(200)


# -- Haptic Output ------------------------------------------------------------

def haptic(pattern, timings=None):
    """Play a haptic pattern string. S=short, L=long, T=tick. Auto-gaps.
    Optional timings dict overrides default durations."""
    if not CAPS.get('haptic'):
        return False
    t = dict(_cfg)
    if timings:
        t.update(timings)
    chars = list(pattern.upper())
    for i, ch in enumerate(chars):
        trailing = i < len(chars) - 1
        if ch == 'S':
            zancig.buzz(t['short_ms'], t['gap_ms'] if trailing else 0)
        elif ch == 'L':
            zancig.buzz(t['long_ms'], t['gap_ms'] if trailing else 0)
        elif ch == 'T':
            zancig.buzz(t['tick_ms'], t['gap_ms'] if trailing else 0)
    return True


def haptic_digit(n):
    """Standard digit encoding: longs=n//4, shorts=n%4.
    Matches zancig.send_digit() output for 1-9."""
    if not 1 <= n <= 9:
        return False
    longs = n // 4
    shorts = n % 4
    pat = 'L' * longs + 'S' * shorts
    return haptic(pat)


def haptic_gap(ms=None):
    """Pause between digit groups. Default: digit_gap_ms."""
    if ms is None:
        ms = _cfg.get('digit_gap_ms', 650)
    time.sleep_ms(ms)


def haptic_ready():
    """Signal: ready (two longs)."""
    haptic('LL')


def haptic_end():
    """Signal: end (three longs)."""
    haptic('LLL')


def haptic_nack():
    """Signal: reject/reset (three fast buzzes)."""
    if not CAPS.get('haptic'):
        return False
    for _ in range(3):
        zancig.buzz(70, 100)
    return True


# -- Sound (stubs -- Watchy has no speaker) ------------------------------------

def tone(freq_hz, duration_ms):
    """Play a tone. Returns False on Watchy (no speaker)."""
    return False


def melody(notes):
    """Play a melody sequence. Returns False on Watchy (no speaker)."""
    return False


def volume(level):
    """Set volume. Returns False on Watchy (no speaker)."""
    return False


# -- Display -------------------------------------------------------------------

def brightness(level):
    """Set display brightness. Returns False on Watchy (e-paper, no backlight)."""
    return False


def set_font_scale(scale):
    """Set the default font scale for show() and show_at(). Clamped 1-12."""
    global _font_scale
    scale = max(1, min(12, int(scale)))
    _font_scale = scale
    return True


def show(lines, title=None):
    """Display a list of strings on screen. Auto-sized, centered per line.
    Returns True if display available, False otherwise."""
    if not CAPS.get('screen'):
        return False
    scale = _font_scale
    zancig.display_clear()
    y = 5
    if title:
        zancig.display_text(title[:12], 5, y, scale=scale)
        y += 8 * scale + 6
        zancig.display_rect(0, y, 200, 1)
        y += 6

    char_w = 8 * scale
    line_h = 8 * scale + 6
    max_chars = 200 // char_w
    for line in lines[:8]:
        text = line[:max_chars]
        x = (200 - len(text) * char_w) // 2
        zancig.display_text(text, x, y, scale=scale)
        y += line_h
        if y > 190:
            break

    zancig.display_show()
    return True


def show_at(text, x, y, scale=None):
    """Draw text at pixel position. Does NOT refresh the display.
    Use refresh() after composing multiple elements."""
    if not CAPS.get('screen'):
        return False
    if scale is None:
        scale = _font_scale
    zancig.display_text(str(text), x, y, scale=scale)
    return True


def draw_rect(x, y, w, h, fill=False):
    """Draw a rectangle. Does NOT refresh the display."""
    if not CAPS.get('screen'):
        return False
    if fill:
        zancig.display_fill_rect(x, y, w, h, colour=1)
    else:
        zancig.display_rect(x, y, w, h)
    return True


def refresh():
    """Push framebuffer to e-paper display (partial refresh)."""
    if not CAPS.get('screen'):
        return False
    zancig.display_show()
    return True


def show_page(lines, page=0, per_page=8, title=None):
    """Paginated display. Returns (success, total_pages)."""
    if not CAPS.get('screen'):
        return (False, 0)
    total = (len(lines) + per_page - 1) // per_page
    if total == 0:
        total = 1
    page = max(0, min(page, total - 1))
    start = page * per_page
    page_lines = lines[start:start + per_page]

    zancig.display_clear()
    y = 5
    scale = _font_scale
    char_w = 8 * scale

    if title:
        zancig.display_text(title[:12], 5, y, scale=scale)
        y += 8 * scale + 6
        zancig.display_rect(0, y, 200, 1)
        y += 6

    line_h = 8 * scale + 6
    max_chars = 200 // char_w
    for line in page_lines:
        text = line[:max_chars]
        x = (200 - len(text) * char_w) // 2
        zancig.display_text(text, x, y, scale=scale)
        y += line_h
        if y > 190:
            break

    if total > 1:
        indicator = f"{page+1}/{total}"
        zancig.display_text(indicator, 200 - len(indicator) * 8, 190, scale=1)

    zancig.display_show()
    return (True, total)


def _auto_scale(lines):
    """Find the largest scale (12..1) that fits all lines on 200x200."""
    n = len(lines)
    max_len = max(len(l) for l in lines) if lines else 1
    for scale in range(12, 0, -1):
        if max_len * 8 * scale > 200:
            continue
        gap = max(2, scale)
        total_h = n * 8 * scale + (n - 1) * gap
        if total_h <= 200:
            return scale
    return 1


def show_large(lines, scale=None, overflow='scale'):
    """Display large text. Accepts string or list.
    scale=None: auto-scale to fit.
    scale=N + overflow='scale': try forced, fall back to auto.
    scale=N + overflow='truncate': clip lines to fit width.
    scale=N + overflow='wrap': hard character wrap."""
    if not CAPS.get('screen'):
        return False

    # Normalize input to list of strings
    if isinstance(lines, (str, int, float)):
        lines = [str(lines)]
    else:
        lines = [str(l) for l in lines]
    lines = lines[:4]

    # Single digit special case
    if len(lines) == 1 and len(lines[0]) == 1 and lines[0].isdigit():
        zancig.display_clear()
        zancig.display_big_digit(int(lines[0]))
        zancig.display_show()
        return True

    # Determine effective scale
    if scale is None:
        eff_scale = _auto_scale(lines)
    else:
        scale = max(1, min(12, int(scale)))
        max_chars = 200 // (8 * scale)
        fits = all(len(l) <= max_chars for l in lines)
        gap = max(2, scale)
        n = len(lines)
        total_h = n * 8 * scale + (n - 1) * gap
        fits = fits and total_h <= 200

        if fits:
            eff_scale = scale
        elif overflow == 'scale':
            eff_scale = _auto_scale(lines)
        elif overflow == 'truncate':
            eff_scale = scale
            lines = [l[:max_chars] for l in lines]
        elif overflow == 'wrap':
            eff_scale = scale
            wrapped = []
            for l in lines:
                while len(l) > max_chars:
                    wrapped.append(l[:max_chars])
                    l = l[max_chars:]
                wrapped.append(l)
            lines = wrapped[:4]
        else:
            eff_scale = _auto_scale(lines)

    # Render centered
    zancig.display_clear()
    n = len(lines)
    gap = max(2, eff_scale)
    total_h = n * 8 * eff_scale + (n - 1) * gap
    y_start = max(0, (200 - total_h) // 2)

    for i, line in enumerate(lines):
        char_w = 8 * eff_scale
        x = max(0, (200 - len(line) * char_w) // 2)
        y = y_start + i * (8 * eff_scale + gap)
        zancig.display_text(line, x, y, scale=eff_scale)

    zancig.display_show()
    return True


def clear():
    """Clear the display."""
    if not CAPS.get('screen'):
        return False
    zancig.display_clear()
    zancig.display_show()
    return True


# -- Input ---------------------------------------------------------------------

def get_digit(lo=1, hi=9, prompt=None, format_fn=None):
    """Full input cycle: device-appropriate jog + confirm button.
    format_fn(n) -> str for extra display during selection.
    No built-in haptic echo -- routine handles its own echo after.
    Short press = confirm, long press = NACK + reset to centre.
    Always returns int -- no exit path (routines must be performance-safe)."""
    if not CAPS.get('accel'):
        return None

    centre = _cfg.get('default_centre', 5)
    centre = max(lo, min(hi, centre))
    confirm_btn = _cfg.get('confirm_btn', 'TR')
    threshold = _cfg.get('tilt_threshold', 300)
    interval = _cfg.get('tick_interval_ms', 800)

    current = centre
    last_displayed = -1
    last_tick_t = time.ticks_ms()

    while True:
        if current != last_displayed:
            _draw_digit_select(current, lo, hi, prompt, format_fn)
            last_displayed = current

        delta = _get_tilt_delta(_neutral)
        now = time.ticks_ms()

        if time.ticks_diff(now, last_tick_t) >= interval:
            if delta > threshold and current > lo:
                current -= 1
                zancig.buzz(_cfg['tick_ms'], _cfg['gap_ms'])
                last_tick_t = now
            elif delta < -threshold and current < hi:
                current += 1
                zancig.buzz(_cfg['tick_ms'], _cfg['gap_ms'])
                last_tick_t = now

        press = zancig.check_button(confirm_btn)
        if press == 'short':
            return current
        if press == 'long':
            haptic_nack()
            current = centre
            last_displayed = -1
            last_tick_t = time.ticks_ms()
            continue

        time.sleep_ms(20)


def get_confirm(prompt=None):
    """Short press = yes (True), long press = no (False)."""
    confirm_btn = _cfg.get('confirm_btn', 'TR')

    if prompt and CAPS.get('screen'):
        show([prompt, '', 'Short=YES', 'Long=NO'])

    while True:
        press = zancig.check_button(confirm_btn)
        if press == 'short':
            return True
        if press == 'long':
            return False

        time.sleep_ms(50)


def wait_press():
    """Block until any button is pressed. Returns button name."""
    while True:
        for name in ('TL', 'TR', 'BL', 'BR'):
            if zancig.check_button(name):
                return name
        time.sleep_ms(50)


# -- Config Passthrough --------------------------------------------------------

def load_config(name, defaults=None):
    """Load routine config. Delegates to zancig."""
    return zancig.load_config(name, defaults)


def save_config(name, data):
    """Save routine config. Delegates to zancig."""
    zancig.save_config(name, data)


# -- Utility -------------------------------------------------------------------

def battery_pct():
    """Returns battery percentage 0-100, or None if unavailable."""
    if not CAPS.get('battery'):
        return None
    return zancig.battery_percent()


def sleep_ms(ms):
    """Platform-appropriate sleep."""
    time.sleep_ms(ms)


# -- Internal helpers ----------------------------------------------------------

def _get_tilt_delta(neutral):
    """Tilt delta using configured axis and direction."""
    nx, ny, nz = neutral
    x, y, z = zancig.accel_xyz()
    d = (x - nx) if _cfg.get('tilt_axis') == 'x' else (y - ny)
    return -d if _cfg.get('tilt_invert') else d


def _draw_digit_select(current, lo, hi, prompt, format_fn):
    """Draw the digit selection screen."""
    if not CAPS.get('screen'):
        return
    zancig.display_clear()
    if prompt:
        zancig.display_text(prompt[:12], 5, 2)
    else:
        zancig.display_text("SELECT", 5, 2)
    zancig.display_rect(0, 20, 200, 1)
    zancig.display_big_digit(current, 52, 28)

    if format_fn:
        extra = format_fn(current)
        if extra:
            extra = str(extra)[:12]
            x = (200 - len(extra) * 16) // 2
            zancig.display_text(extra, x, 135)

    zancig.display_text(f"{lo}-{hi}", 5, 185, scale=1)
    zancig.display_show()
