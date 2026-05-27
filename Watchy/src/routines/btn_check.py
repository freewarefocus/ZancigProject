"""
routines/btn_check.py
Button mapping sanity check. Press any button, see its name and position.
Long press any button to exit.
"""
import zri
import zancig


def run():
    zri.init()
    labels = {
        'TL': ['TL  BACK', 'top-left'],
        'TR': ['TR  UP', 'top-right'],
        'BL': ['BL  MENU', 'bottom-left'],
        'BR': ['BR  DOWN', 'bottom-right'],
    }
    zri.show(['BTN CHECK', '', 'press any', 'button'])

    while True:
        for name in ('TL', 'TR', 'BL', 'BR'):
            press = zancig.check_button(name)
            if press is None:
                continue
            if press == 'long':
                zri.show(['DONE'])
                zri.sleep_ms(500)
                return
            zri.show_large(labels[name])
            zri.sleep_ms(1500)
            zri.show(['BTN CHECK', '', 'press any', 'button'])
        zri.sleep_ms(50)
