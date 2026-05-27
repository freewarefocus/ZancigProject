"""
main.py -- Zancig launcher
Auto-runs on device boot. Shows routine menu on screen.
Three-state power model: Active -> Dark -> Deep Sleep.
UP (TR): short=cycle, long=launch routine
MENU (BL): long=Python mode (240MHz, drops to REPL for Thonny)
USB connected: sleep timers disabled (stays active for file transfer)
"""
import zancig
import zri
import time
from machine import freq

IDLE_TIMEOUT_MS = 30_000    # 30s no input -> blank screen (dark mode)
SLEEP_GRACE_MS  = 10_000    # 10s more -> deep sleep
BATT_INTERVAL   = 300_000   # 5 min battery check
INPUT_POLL_MS   = 5_000     # Active poll cycle
DARK_POLL_MS    = 2_000     # Dark mode poll cycle


def wait_menu_input(timeout_ms=5_000):
    """Poll TR and BL buttons. Returns (button, press_type) or None on timeout."""
    btns = zancig._btns
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
        for name in ('TR', 'BL'):
            if btns[name].value() == zancig.BTN_ACTIVE:
                t = time.ticks_ms()
                while btns[name].value() == zancig.BTN_ACTIVE:
                    time.sleep_ms(10)
                ms = time.ticks_diff(time.ticks_ms(), t)
                kind = 'long' if ms >= zancig.LONG_PRESS_MS else 'short'
                return name, kind
        time.sleep_ms(100)
    return None


def enter_python_mode():
    freq(240_000_000)
    zancig.display_clear()
    zancig.display_text("PYTHON MODE", 20, 40)
    zancig.display_text("240MHz REPL", 20, 60)
    zancig.display_text("Thonny>>", 20, 100)
    zancig.display_text("Ctrl+D boot", 20, 120)
    zancig.display_show()


def enter_deep_sleep():
    """Blank screen, suspend peripherals, deep sleep. Wakes on any button (full reboot).
    GPIO 0 (TR) excluded from wake mask: boot strap pin floats low during
    deep sleep (ESP-IDF strips RTC pull-ups via rtcio_hal_isolate on EXT1 pins).
    TL/BL/BR still wake the device — any button returns to menu."""
    import esp32
    from machine import Pin, deepsleep
    zancig.prepare_sleep()
    wake_pins = [
        Pin(7, Pin.IN, Pin.PULL_UP),   # BL (MENU)
        Pin(6, Pin.IN, Pin.PULL_UP),   # TL (BACK)
        Pin(8, Pin.IN, Pin.PULL_UP),   # BR (DOWN)
    ]
    esp32.wake_on_ext1(wake_pins, esp32.WAKEUP_ALL_LOW)
    deepsleep()


def main():
    zri.init()
    routines = zancig.list_routines()

    if not routines:
        zancig.display_clear()
        zancig.display_text("No routines", 20, 90)
        zancig.display_show()
        return

    freq(80_000_000)
    idx = 0
    last_idx = -1
    last_batt_ms = 0
    last_activity_ms = time.ticks_ms()
    is_dark = False

    while True:
        now = time.ticks_ms()
        idle_ms = time.ticks_diff(now, last_activity_ms)

        # Skip sleep transitions when USB is connected (charging / file transfer)
        usb = zancig.is_usb_connected()

        # Deep sleep check: dark mode exceeded grace period
        if is_dark and not usb and idle_ms >= IDLE_TIMEOUT_MS + SLEEP_GRACE_MS:
            enter_deep_sleep()

        # Dark mode check: idle exceeded timeout
        if not is_dark and not usb and idle_ms >= IDLE_TIMEOUT_MS:
            zancig.display_clear()
            zancig.display_show()
            is_dark = True

        # Draw menu (only when active and needed)
        if not is_dark:
            need_redraw = (idx != last_idx) or time.ticks_diff(now, last_batt_ms) >= BATT_INTERVAL
            if need_redraw:
                pct = zancig.battery_percent()
                last_batt_ms = time.ticks_ms()
                if pct <= 5:
                    zancig.display_clear()
                    zancig.display_text("LOW BATTERY", 10, 70)
                    zancig.display_text(f"{pct}%", 80, 110)
                    zancig.display_show_full()
                    time.sleep(3)
                    enter_deep_sleep()
                mhz = freq() // 1_000_000
                batt_str = f"!{pct}%" if pct <= 15 else f"{pct}%"
                zancig.display_clear()
                zancig.display_text("ZANCIG", 5, 5)
                zancig.display_text(f"{mhz}MHz {batt_str}", 5, 25)
                zancig.display_rect(0, 44, 200, 1)
                for i, name in enumerate(routines):
                    marker = ">" if i == idx else " "
                    zancig.display_text(f"{marker}{name[:10]}", 5, 50 + i * 20)
                zancig.display_show()
                last_idx = idx

        # Poll input (shorter timeout when dark)
        poll_ms = DARK_POLL_MS if is_dark else INPUT_POLL_MS
        result = wait_menu_input(poll_ms)
        if result is None:
            continue

        # Any button press resets activity
        last_activity_ms = time.ticks_ms()

        # Wake from dark mode: redraw menu, consume the press
        if is_dark:
            is_dark = False
            last_idx = -1  # force redraw
            last_batt_ms = 0
            continue

        btn, press = result
        if btn == 'TR' and press == 'short':
            idx = (idx + 1) % len(routines)
        elif btn == 'TR' and press == 'long':
            last_idx = -1
            freq(160_000_000)
            try:
                zancig.run_routine(routines[idx])
            except Exception as e:
                zancig.display_clear()
                zancig.display_text("ERROR", 5, 5)
                zancig.display_rect(0, 22, 200, 1)
                msg = str(e)
                for i in range(0, len(msg), 12):
                    zancig.display_text(msg[i:i+12], 5, 30 + (i//12)*20)
                    if 30 + (i//12)*20 > 170:
                        break
                zancig.display_show_full()
                time.sleep(5)
            freq(80_000_000)
            last_activity_ms = time.ticks_ms()
        elif btn == 'BL' and press == 'long':
            enter_python_mode()
            return  # exits to REPL


main()
