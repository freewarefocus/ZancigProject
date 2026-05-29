"""
zancig.py -- Zancig Hardware Framework for Watchy V3 (MicroPython)
All GPIO constants match HARDWARE_MAP.md for Watchy V3 (ESP32-S3).
"""

from machine import Pin, SPI, I2C, ADC, freq
import framebuf
import time
import struct

# -- Hardware constants (Watchy V3) -------------------------------------------

MOTOR_PIN   = 17
BTN_TL      = 6    # BACK  (top-left)
BTN_TR      = 0    # UP    (top-right,    also boot strap pin)
BTN_BL      = 7    # MENU  (bottom-left)
BTN_BR      = 8    # DOWN  (bottom-right)

EPD_CS      = 33
EPD_DC      = 34
EPD_RST     = 35
EPD_BUSY    = 36
EPD_SCK     = 47
EPD_MOSI    = 48

BMA_SDA     = 12
BMA_SCL     = 11
BMA_ADDR    = 0x18

BATT_PIN    = 9

# -- Haptic timing constants --------------------------------------------------

SHORT_MS    = 120
LONG_MS     = 380
GAP_MS      = 200
DIGIT_GAP   = 650
MOVE_GAP    = 1100
TICK_UP_MS  = 80
TICK_DOWN_MS = 120

# -- Button timing -------------------------------------------------------------

LONG_PRESS_MS  = 600
BTN_ACTIVE     = 0   # active LOW (pull-up)

# -- Jog dial constants --------------------------------------------------------

TICK_INTERVAL_MS = 800
TILT_THRESHOLD   = 300

# -- Hardware state (set by init()) --------------------------------------------

_motor = None
_btns  = {}
_epd   = None
_fb    = None
_buf   = None
_bma   = None
_batt  = None
_needs_full = True
_boot_ms = 0


def init():
    """Call once at startup to initialise all hardware."""
    global _motor, _btns, _epd, _fb, _buf, _bma, _batt, _needs_full, _boot_ms

    _boot_ms = time.ticks_ms()

    # Power management: lower CPU clock, disable radio
    freq(80_000_000)
    try:
        import network
        network.WLAN(network.STA_IF).active(False)
    except Exception:
        pass

    _motor = Pin(MOTOR_PIN, Pin.OUT)

    _phys = {
        'TL': Pin(BTN_TL, Pin.IN, Pin.PULL_UP),
        'TR': Pin(BTN_TR, Pin.IN, Pin.PULL_UP),
        'BL': Pin(BTN_BL, Pin.IN, Pin.PULL_UP),
        'BR': Pin(BTN_BR, Pin.IN, Pin.PULL_UP),
    }
    _btn_defaults = {'TL': 'TL', 'TR': 'TR', 'BL': 'BL', 'BR': 'BR'}
    try:
        ns = {}
        with open('/zancig_cfg.py') as f:
            exec(f.read(), ns)
        btn_cfg = dict(_btn_defaults)
        btn_cfg.update(ns['config'])
    except Exception:
        btn_cfg = _btn_defaults
    _btns = {}
    for name in ('TL', 'TR', 'BL', 'BR'):
        target = btn_cfg.get(name, name)
        _btns[name] = _phys[target] if target in _phys else _phys[name]

    from epd_driver import EPD
    _epd = EPD()

    _buf = bytearray(200 * 200 // 8)
    _fb  = framebuf.FrameBuffer(_buf, 200, 200, framebuf.MONO_HLSB)

    i2c = I2C(0, scl=Pin(BMA_SCL), sda=Pin(BMA_SDA), freq=400000)
    from bma423 import BMA423
    _bma = BMA423(i2c, BMA_ADDR)

    _batt = ADC(Pin(BATT_PIN))
    _batt.atten(ADC.ATTN_11DB)

    _needs_full = True


# -- Motor / Haptics -----------------------------------------------------------

def buzz(on_ms, off_ms=0):
    _motor.on()
    time.sleep_ms(on_ms)
    _motor.off()
    if off_ms:
        time.sleep_ms(off_ms)

def tick_up():
    buzz(TICK_UP_MS, GAP_MS)

def tick_down():
    buzz(TICK_DOWN_MS, GAP_MS)

def pulse_short(trailing=True):
    buzz(SHORT_MS, GAP_MS if trailing else 0)

def pulse_long(trailing=True):
    buzz(LONG_MS, GAP_MS if trailing else 0)

def send_digit(n):
    """
    Encode digit 1-9 as haptic pulses.
    1=*  2=**  3=***  4=-  5=-*  6=-**  7=-***  8=--  9=--*
    """
    if not 1 <= n <= 9:
        raise ValueError(f"Digit out of range: {n}")
    longs  = n // 4
    shorts = n % 4
    for i in range(longs):
        pulse_long(trailing=(shorts > 0 or i < longs - 1))
    for i in range(shorts):
        pulse_short(trailing=(i < shorts - 1))

def send_coordinate(row, col):
    send_digit(row)
    time.sleep_ms(DIGIT_GAP)
    send_digit(col)

def send_ready():
    pulse_long()
    time.sleep_ms(GAP_MS)
    pulse_long()

def send_end():
    for i in range(3):
        pulse_long(trailing=(i < 2))

def send_nack():
    for _ in range(3):
        buzz(70, 100)

def send_ack_echo(n):
    time.sleep_ms(300)
    send_digit(n)


# -- Buttons -------------------------------------------------------------------

def wait_button(btn_name='TR'):
    """Block until named button pressed. Returns 'short' or 'long'."""
    btn = _btns[btn_name]
    while btn.value() != BTN_ACTIVE:
        time.sleep_ms(50)
    t = time.ticks_ms()
    while btn.value() == BTN_ACTIVE:
        time.sleep_ms(10)  # tight polling during press measurement
    ms = time.ticks_diff(time.ticks_ms(), t)
    return 'long' if ms >= LONG_PRESS_MS else 'short'

def check_button(btn_name='TR'):
    """Non-blocking. Returns 'short', 'long', or None."""
    btn = _btns[btn_name]
    if btn.value() != BTN_ACTIVE:
        return None
    return wait_button(btn_name)


# -- Battery -------------------------------------------------------------------

def battery_voltage():
    """Read battery voltage. V3 has a 1:2 voltage divider on GPIO 9."""
    # V3 has ~500ms GPIO spike after boot -- wait it out
    elapsed = time.ticks_diff(time.ticks_ms(), _boot_ms)
    if elapsed < 600:
        time.sleep_ms(600 - elapsed)
    samples = []
    for _ in range(5):
        samples.append(_batt.read_uv())
        time.sleep_ms(2)
    samples.sort()
    avg = (samples[1] + samples[2] + samples[3]) // 3
    return avg * 2 / 1_000_000

_BATT_TABLE = (
    (4.20, 100), (4.10, 90), (4.00, 80), (3.90, 60),
    (3.80, 40), (3.70, 20), (3.60, 10), (3.50, 5), (3.30, 0),
)

def battery_percent():
    """Return battery percentage (0-100), mapped to LiPo discharge curve."""
    v = battery_voltage()
    if v >= _BATT_TABLE[0][0]:
        return 100
    if v <= _BATT_TABLE[-1][0]:
        return 0
    for i in range(len(_BATT_TABLE) - 1):
        v_hi, p_hi = _BATT_TABLE[i]
        v_lo, p_lo = _BATT_TABLE[i + 1]
        if v >= v_lo:
            return int(p_lo + (v - v_lo) / (v_hi - v_lo) * (p_hi - p_lo))
    return 0


# -- Power Management ----------------------------------------------------------

def prepare_sleep():
    """Prepare all hardware for deep sleep."""
    _motor.off()
    try:
        _bma.suspend()
    except Exception:
        pass
    display_clear()
    display_show()          # Fast partial refresh to blank screen
    _epd.sleep()            # EPD deep sleep (zero power, retains blank image)


def is_usb_connected():
    """Check USB presence via GPIO 21."""
    return Pin(21, Pin.IN).value() == 1


# -- Accelerometer -------------------------------------------------------------

def accel_xyz():
    return _bma.read_xyz()

def calibrate_neutral():
    """Read current orientation as neutral. Returns (x, y, z) baseline."""
    return _bma.read_xyz()

def get_jog_delta(neutral_xyz):
    """
    Returns signed integer offset from neutral orientation.
    Positive = tilted one way, negative = other way.
    CONFIRM axis in Phase 6 calibration.
    """
    nx, ny, nz = neutral_xyz
    x,  y,  z  = _bma.read_xyz()
    return y - ny


# -- Jog Dial Input ------------------------------------------------------------

def read_digit(btn_name='TR', centre=5, lo=1, hi=9):
    """
    Full jog dial input with haptic echo and ACK/NACK loop.
    Returns confirmed digit (int).
    """
    while True:
        neutral = calibrate_neutral()
        current = centre
        last_tick_t = time.ticks_ms()

        while True:
            delta = get_jog_delta(neutral)
            now   = time.ticks_ms()

            if time.ticks_diff(now, last_tick_t) >= TICK_INTERVAL_MS:
                if delta > TILT_THRESHOLD and current > lo:
                    current -= 1
                    tick_down()
                    last_tick_t = now
                elif delta < -TILT_THRESHOLD and current < hi:
                    current += 1
                    tick_up()
                    last_tick_t = now

            press = check_button(btn_name)
            if press == 'short':
                break
            if press == 'long':
                send_nack()
                break

            time.sleep_ms(20)
        else:
            continue

        # Echo phase
        send_ack_echo(current)

        # ACK/NACK wait
        while True:
            press = wait_button(btn_name)
            if press == 'short':
                return current
            if press == 'long':
                send_nack()
                break

def read_coordinate(btn_name='TR'):
    """Read two confirmed digits. Returns (row, col) tuple."""
    row = read_digit(btn_name)
    col = read_digit(btn_name)
    return row, col


# -- Display -------------------------------------------------------------------

def display_clear(colour=0):
    _fb.fill(colour)

def display_text(text, x, y, colour=1, scale=2):
    if scale <= 1:
        _fb.text(text, x, y, colour)
        return
    tmp = bytearray(8)
    tmp_fb = framebuf.FrameBuffer(tmp, 8, 8, framebuf.MONO_HLSB)
    for i, ch in enumerate(text):
        tmp_fb.fill(1 - colour)
        tmp_fb.text(ch, 0, 0, colour)
        cx = x + i * 8 * scale
        for row in range(8):
            for col in range(8):
                if tmp_fb.pixel(col, row) == colour:
                    _fb.fill_rect(cx + col * scale, y + row * scale,
                                  scale, scale, colour)

def display_rect(x, y, w, h, colour=1):
    _fb.rect(x, y, w, h, colour)

def display_fill_rect(x, y, w, h, colour=0):
    _fb.fill_rect(x, y, w, h, colour)

def display_show():
    """Write framebuffer to e-paper and trigger partial refresh (~0.3s).
    No flash -- stealth default. Use display_show_full() for ghosting cleanup.
    First call after init() auto-promotes to full refresh (baseline needed).
    Uses power_off (not deep sleep) to preserve RAM baseline between partials."""
    global _needs_full
    if _needs_full:
        display_show_full()
        _needs_full = False  # clear AFTER full, since display_show_full() sets it
        return
    _epd.init()
    _epd.write_image(0, 0, 200, 200, _buf)       # new data -> 0x24
    _epd.update_partial()                          # 0xFF: self-contained power+update+disable
    _epd.write_image_prev(0, 0, 200, 200, _buf)  # sync baseline -> 0x26 for next partial

def display_show_full():
    """Write framebuffer and trigger full refresh (~2s, flashes).
    Writes both RAMs to establish baseline for future partial refreshes.
    Use periodically to clean ghosting from partial refreshes."""
    global _needs_full
    _epd.init()
    _epd.power_on()
    _epd.write_image_both(0, 0, 200, 200, _buf)
    _epd.update_full()
    _epd.sleep()
    _needs_full = True  # deep sleep clears baseline; next show() must re-establish

def display_big_digit(n, x=60, y=40, colour=1):
    """Draw a large single digit using scaled 8x8 font."""
    tmp = bytearray(8)
    tmp_fb = framebuf.FrameBuffer(tmp, 8, 8, framebuf.MONO_HLSB)
    tmp_fb.fill(0)
    tmp_fb.text(str(n), 0, 0, 1)

    scale = 12
    for row in range(8):
        for col in range(8):
            if tmp_fb.pixel(col, row):
                _fb.fill_rect(x + col * scale, y + row * scale,
                              scale - 1, scale - 1, colour)

def display_word_list(words, title=None):
    """Display a list of candidate words on screen."""
    display_clear()
    y = 5
    if title:
        display_text(title[:12], 5, y)
        y += 20
        display_rect(0, y, 200, 1)
        y += 6

    line_h = 22
    for word in words[:8]:
        display_text(word.upper()[:12], 10, y)
        y += line_h
        if y > 190:
            break

    display_show()

def display_number_large(n):
    """Show a single large number, black background."""
    display_clear()
    display_big_digit(n)
    display_show()


# -- Config --------------------------------------------------------------------

def load_config(name, defaults=None):
    """Load /routines/{name}_cfg.py config dict, merged with defaults.
    Creates bare config file on first run if no file exists.
    Falls back to defaults silently on syntax errors."""
    cfg = dict(defaults) if defaults else {}
    try:
        ns = {}
        with open(f'/routines/{name}_cfg.py') as f:
            exec(f.read(), ns)
        cfg.update(ns['config'])
    except OSError:
        if defaults:
            save_config(name, cfg)
    except Exception:
        pass
    return cfg

def save_config(name, data):
    """Write config dict as /routines/{name}_cfg.py (no comments)."""
    with open(f'/routines/{name}_cfg.py', 'w') as f:
        f.write('config = {\n')
        for k, v in data.items():
            f.write(f'    {repr(k)}: {repr(v)},\n')
        f.write('}\n')


# -- Routine Loader ------------------------------------------------------------

def list_routines():
    """Return list of available routine names (filenames without .py)."""
    import os
    try:
        files = os.listdir('/routines')
        return [f[:-3] for f in files
                if f.endswith('.py') and not f.endswith('_cfg.py')]
    except OSError:
        return []

def run_routine(name):
    """Dynamically import and run a routine by name."""
    import sys
    mod_path = f'routines.{name}'
    if mod_path in sys.modules:
        del sys.modules[mod_path]
    __import__(mod_path)
    mod = sys.modules[mod_path]
    mod.run()
