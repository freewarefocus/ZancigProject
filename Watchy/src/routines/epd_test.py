"""
routines/epd_test.py
Diagnostic: cycle through partial refresh strategies to find the one that works.
UP (TL): cycle digit 1->2->3->1 (redraws with current strategy)
DOWN (BR): switch to next strategy (full refresh resets baseline first)
BACK (BL): exit to menu

Strategies target specific SSD1681 command 0x22 values:
  S1 0xFC: current code -- power_on(0xE0), update(0xFC), power_off(0x83)
  S2 0xFF: self-contained -- no separate power_on/off, update(0xFF) does it all
  S3 pwrF8: power_on(0xF8) instead of 0xE0, update(0xFC), power_off
  S4 F8+FF: power_on(0xF8), update(0xFF), no power_off (0xFF self-disables)
  S5 FULL: full refresh control (always clean, flashes)
"""
import zancig
import time

STRATEGIES = ['0xFC', '0xFF', 'pwrF8', 'F8+FF', 'FULL']
DIGITS = [1, 2, 3]


def draw_screen(digit, strat_idx):
    """Draw digit and strategy label into framebuffer."""
    zancig.display_clear()
    zancig.display_text(STRATEGIES[strat_idx], 5, 5)
    zancig.display_text(f"S{strat_idx+1}/{len(STRATEGIES)}", 130, 5, scale=1)
    zancig.display_rect(0, 22, 200, 1)
    zancig.display_big_digit(digit)
    zancig.display_text("TL:dig BR:strat", 5, 180, scale=1)


def _cmd(cmd, data):
    """Send a single command+data byte to the EPD controller."""
    epd = zancig._epd
    epd.send_command(cmd)
    epd.send_data(data)


def show_0xFC():
    """S1: Current code -- power_on(0xE0), write 0x24, update(0xFC), write 0x26, power_off(0x83)."""
    epd = zancig._epd
    buf = zancig._buf
    epd.init()
    epd.power_on()                              # 0x22=0xE0
    epd.write_image(0, 0, 200, 200, buf)        # -> 0x24
    epd.update_partial()                         # 0x22=0xFC
    epd.write_image_prev(0, 0, 200, 200, buf)  # -> 0x26
    epd.power_off()                              # 0x22=0x83


def show_0xFF():
    """S2: Self-contained -- no power_on/off, update(0xFF) handles everything."""
    epd = zancig._epd
    buf = zancig._buf
    epd.init()
    # No power_on -- 0xFF enables clock+analog itself
    epd.write_image(0, 0, 200, 200, buf)        # -> 0x24
    _cmd(0x22, 0xFF)                             # self-contained partial update
    epd.send_command(0x20)
    epd.wait_while_busy(5000)
    epd.write_image_prev(0, 0, 200, 200, buf)  # -> 0x26
    # No power_off -- 0xFF disables clock+analog itself


def show_pwrF8():
    """S3: GxEPD2 power_on value -- power_on(0xF8), update(0xFC), power_off."""
    epd = zancig._epd
    buf = zancig._buf
    epd.init()
    _cmd(0x22, 0xF8)                             # power_on with 0xF8 (GxEPD2 style)
    epd.send_command(0x20)
    epd.wait_while_busy(5000)
    epd.write_image(0, 0, 200, 200, buf)        # -> 0x24
    epd.update_partial()                         # 0x22=0xFC
    epd.write_image_prev(0, 0, 200, 200, buf)  # -> 0x26
    epd.power_off()                              # 0x22=0x83


def show_F8_FF():
    """S4: GxEPD2 power_on(0xF8) + self-contained update(0xFF)."""
    epd = zancig._epd
    buf = zancig._buf
    epd.init()
    _cmd(0x22, 0xF8)                             # power_on GxEPD2 style
    epd.send_command(0x20)
    epd.wait_while_busy(5000)
    epd.write_image(0, 0, 200, 200, buf)        # -> 0x24
    _cmd(0x22, 0xFF)                             # self-contained partial + power down
    epd.send_command(0x20)
    epd.wait_while_busy(5000)
    epd.write_image_prev(0, 0, 200, 200, buf)  # -> 0x26


def show_full():
    """S5: Full refresh control (always clean, flashes)."""
    zancig.display_show_full()


SHOW_FNS = [show_0xFC, show_0xFF, show_pwrF8, show_F8_FF, show_full]


def poll_buttons():
    """Non-blocking button poll. Returns ('TL'|'BR'|'BL', 'short'|'long') or None."""
    btns = zancig._btns
    for name in ('TL', 'BR', 'BL'):
        if btns[name].value() == zancig.BTN_ACTIVE:
            t = time.ticks_ms()
            while btns[name].value() == zancig.BTN_ACTIVE:
                time.sleep_ms(10)
            ms = time.ticks_diff(time.ticks_ms(), t)
            kind = 'long' if ms >= zancig.LONG_PRESS_MS else 'short'
            return name, kind
    return None


def run():
    strat_idx = 0
    digit_idx = 0

    # Initial draw with full refresh to establish baseline
    draw_screen(DIGITS[digit_idx], strat_idx)
    zancig.display_show_full()

    while True:
        time.sleep_ms(50)
        result = poll_buttons()
        if result is None:
            continue

        btn, kind = result

        if btn == 'BL':
            return

        if btn == 'TL':
            # Cycle digit, redraw with current strategy
            digit_idx = (digit_idx + 1) % len(DIGITS)
            draw_screen(DIGITS[digit_idx], strat_idx)
            SHOW_FNS[strat_idx]()

        elif btn == 'BR':
            # Switch strategy, full refresh to reset baseline
            strat_idx = (strat_idx + 1) % len(STRATEGIES)
            digit_idx = 0
            draw_screen(DIGITS[digit_idx], strat_idx)
            zancig.display_show_full()
