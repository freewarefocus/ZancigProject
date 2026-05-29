"""
routines/zri_test.py
ZRI library exerciser. Steps through API functions one by one,
displaying the test name before each call so a crash points to the culprit.
Short press (TL) = advance to next test. Long press = skip to end.
"""
import zri


def _label(text):
    """Show test label and wait for button press to proceed."""
    zri.show(['ZRI TEST', '', text])
    btn = zri.wait_press()
    return btn


def _pass(detail=None):
    """Flash PASS (with optional detail) briefly."""
    lines = ['PASS']
    if detail is not None:
        lines.append(str(detail))
    zri.show(lines)
    zri.sleep_ms(600)


def run():
    zri.init()

    # -- CAPS --
    _label('CAPS check')
    caps = zri.CAPS
    _pass(f"h={caps.get('haptic')} s={caps.get('screen')}")

    # -- battery_pct --
    _label('battery_pct()')
    pct = zri.battery_pct()
    _pass(f'{pct}%')

    # -- stealth --
    _label('stealth()')
    zri.stealth()
    zri.sleep_ms(1000)
    _pass()

    # -- clear --
    _label('clear()')
    zri.clear()
    zri.sleep_ms(500)
    _pass()

    # -- show basic --
    _label('show(lines)')
    zri.show(['LINE 1', 'LINE 2', 'LINE 3'])
    zri.sleep_ms(1000)
    _pass()

    # -- show with title --
    _label('show(title=)')
    zri.show(['body line'], title='TITLED')
    zri.sleep_ms(1000)
    _pass()

    # -- show_large single digit --
    _label('show_large(5)')
    zri.show_large('5')
    zri.sleep_ms(1000)
    _pass()

    # -- show_large word --
    _label('show_large HI')
    zri.show_large('HI')
    zri.sleep_ms(1000)
    _pass()

    # -- show_large multi-line --
    _label('show_large multi')
    zri.show_large(['AB', 'CD'])
    zri.sleep_ms(1000)
    _pass()

    # -- show_large auto-scale long text --
    _label('show_large auto')
    zri.show_large('LONGWORD')
    zri.sleep_ms(1000)
    _pass()

    # -- show_large forced scale + truncate --
    _label('large truncate')
    zri.show_large(['TRUNCATEME'], scale=6, overflow='truncate')
    zri.sleep_ms(1000)
    _pass()

    # -- show_large forced scale + wrap --
    _label('large wrap')
    zri.show_large(['WRAPTHISLINE'], scale=4, overflow='wrap')
    zri.sleep_ms(1000)
    _pass()

    # -- show_large forced scale + scale fallback --
    _label('large fallback')
    zri.show_large(['TOOBIG'], scale=12, overflow='scale')
    zri.sleep_ms(1000)
    _pass()

    # -- set_font_scale + show --
    _label('font_scale 3')
    zri.set_font_scale(3)
    zri.show(['SCALE 3'])
    zri.sleep_ms(1000)
    zri.set_font_scale(2)  # restore
    _pass()

    # -- show_at + draw_rect + refresh (batch drawing) --
    _label('batch draw')
    zri.clear()
    zri.show_at('TOP-L', 5, 5)
    zri.show_at('BOT-R', 100, 170)
    zri.draw_rect(0, 0, 200, 200)
    zri.draw_rect(50, 50, 100, 100, fill=True)
    zri.refresh()
    zri.sleep_ms(1500)
    _pass()

    # -- show_page --
    _label('show_page')
    pages = [f'ITEM {i}' for i in range(20)]
    ok, total = zri.show_page(pages, page=0, title='PAGE')
    _pass(f'p1 of {total}')

    _label('show_page p2')
    zri.show_page(pages, page=1, title='PAGE')
    zri.sleep_ms(1000)
    _pass()

    # -- brightness stub --
    _label('brightness(50)')
    result = zri.brightness(50)
    _pass(f'ret={result}')

    # -- sound stubs --
    _label('tone() stub')
    result = zri.tone(440, 100)
    _pass(f'ret={result}')

    _label('melody() stub')
    result = zri.melody([('C4', 100)])
    _pass(f'ret={result}')

    _label('volume() stub')
    result = zri.volume(50)
    _pass(f'ret={result}')

    # -- haptic --
    _label('haptic SLS')
    zri.haptic('SLS')
    _pass()

    # -- haptic tick_up / tick_down --
    _label('haptic UD')
    zri.haptic('UD')
    _pass()

    # -- haptic_digit --
    _label('haptic_digit 7')
    zri.haptic_digit(7)
    _pass()

    # -- haptic_gap --
    _label('haptic_gap')
    zri.haptic_gap()
    _pass()

    # -- haptic_ready --
    _label('haptic_ready')
    zri.haptic_ready()
    _pass()

    # -- haptic_end --
    _label('haptic_end')
    zri.haptic_end()
    _pass()

    # -- haptic_nack --
    _label('haptic_nack')
    zri.haptic_nack()
    _pass()

    # -- sleep_ms --
    _label('sleep_ms 500')
    zri.sleep_ms(500)
    _pass()

    # -- done --
    zri.show(['ALL TESTS', 'PASSED', '', 'press=exit'])
    zri.wait_press()
    zri.done()
