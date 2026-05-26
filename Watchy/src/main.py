"""
main.py -- Zancig launcher
Auto-runs on device boot. Shows routine menu on screen.
UP (TL): short=cycle, long=launch routine
MENU (TR): long=Python mode (240MHz, drops to REPL for Thonny)
"""
import zancig
import zri
import time
from machine import freq


def wait_menu_input(timeout_ms=600_000):
    """Poll both TL and TR buttons. Returns (button, press_type) or None on timeout."""
    btns = zancig._btns
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
        for name in ('TL', 'TR'):
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
    BATT_INTERVAL = 300_000  # 5 minutes
    while True:
        now = time.ticks_ms()
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
                import machine
                machine.deepsleep()
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

        result = wait_menu_input()
        if result is None:
            continue
        btn, press = result
        if btn == 'TL' and press == 'short':
            idx = (idx + 1) % len(routines)
        elif btn == 'TL' and press == 'long':
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
        elif btn == 'TR' and press == 'long':
            enter_python_mode()
            return  # exits to REPL


main()
