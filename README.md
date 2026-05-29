# Project Zancig

A covert performance assistant for mentalists and magicians.

---

## What This Is

Zancig is a concealed electronic assistant for solo performers. You palm it, wear it, or pocket it. During a performance, it accepts secret input (button presses, tilts, slides) and feeds information back to you covertly through haptic vibration patterns and discreet screen peeks.

Use cases include book tests, knight's tour demonstrations, day-of-the-week calculations, number memorization reveals, and any effect where the performer needs hidden access to computed or stored information.

Everything is configurable per performer -- haptic timing and encoding, button assignments, left- or right-handed input, tilt sensitivity, confirm gestures. Commercial mentalism devices might let you pick a hand. Zancig lets you tune every parameter until the device feels like an extension of your body.

The audience sees nothing. No phone. No earpiece. No assistant.

---

## How It Works

Every Zancig routine follows the same covert I/O loop:

1. **Secret input** -- The performer enters information using button presses or accelerometer tilt (a jog-dial gesture) while the device is palmed, hidden in a pocket or under a sleeve.
2. **Computation** -- The routine processes the input (a lookup, a calculation, a mapping).
3. **Covert output** -- The result comes back as a haptic vibration pattern (e.g., short-short-long = digit 7) or as text on a screen the performer peeks at during a natural gesture.

Haptic output works eyes-free and fully concealed. Screen output requires a brief glance but can convey more information. The performer chooses which mode fits the moment.

---

## Supported Hardware

### Watchy V3 (active)

The [Watchy](https://watchy.sqfmi.com/) by SQFMI is an open-source e-paper smartwatch based on the ESP32-S3. Its watch form factor and palmability provides natural cover for performance use.

- MCU: ESP32-S3
- Display: 200x200 e-paper
- Input: 4 physical buttons + BMA423 accelerometer (tilt jog dial)
- Haptic: ERM vibration motor via DRV2605L driver
- Runtime: MicroPython
- Status: **Active**

Hardware pin assignments and peripheral details used in the Zancig Watchy implementation were sourced from [Watchy_GSR](https://github.com/GuruSR/Watchy_GSR) by GuruSR, whose comprehensive V3 hardware documentation was instrumental in establishing accurate specifications for the MicroPython port.

### Thumby Color (planned)

The [Thumby Color](https://thumby.us/) by TinyCircuits is a miniature handheld game device based on the RP2350. Its tiny form factor makes it concealable in a palm.

- MCU: RP2350
- Display: Color LCD
- Input: D-pad + A/B buttons
- Haptic: ERM vibration motor
- Runtime: MicroPython
- Status: **Planned**

---

## Routines

Routines are the performance effects Zancig enables -- book tests, day-of-the-week calculations, knight's tour demonstrations, and so on. Each routine is a plain MicroPython `.py` file with a `run()` function. The launcher discovers routines automatically and presents them in a menu.

The design goal is **write once, use on any Zancig device.** A routine written for Watchy should run unchanged on Thumby Color or any future platform, as long as it only uses capabilities both devices share. This isn't always possible -- a routine that uses `show_large()` (display text on screen) won't work on a hypothetical device without a screen -- but it is the ideal every routine aims for.

Routines don't hardcode timing, buttons, or encoding. Those live in a separate config file (`zri_cfg.py`) that the performer edits to match their preferences -- which hand they use, how fast the haptic pulses feel comfortable, which button confirms a selection. A routine author writes the logic; the performer tunes the feel.

Routines live under `src/routines/` on each device. Contributions are welcome.

---

## ZRI (Zancig Routine Interface)

Routines achieve device portability by never talking to hardware directly. Instead, they import `zri` -- a device-agnostic API layer that handles all input, output, and device differences. Each supported device has its own `zri.py` implementation. Routines import only `zri` and run unchanged on any device that meets their capability requirements.

A `CAPS` dictionary lets routines check what the current device supports:

```python
import zri

zri.init()
if zri.CAPS.get('sound'):
    zri.tone(440, 200)
```

### Minimal routine example

```python
"""A simple routine: enter a digit, buzz it back."""
import zri

def run():
    zri.init()
    zri.haptic_ready()

    digit = zri.get_digit()
    zri.haptic_digit(digit)
    zri.show_large(str(digit))

    zri.wait_press()
    zri.done()
```

Routines are plain `.py` files with a `run()` function. The launcher (`main.py`) discovers and presents them in a menu.

### Key API areas

- **Lifecycle:** `init()`, `stealth()`, `done()`
- **Input:** `get_digit()`, `get_confirm()`, `wait_press()`
- **Haptic:** `haptic()`, `haptic_digit()`, `haptic_ready()`, `haptic_end()`, `haptic_nack()`
- **Display:** `show()`, `show_large()`, `show_page()`, `clear()`
- **Sound:** `tone()`, `melody()`, `volume()` (device-dependent, check `CAPS['sound']`)
- **Config:** `load_config()`, `save_config()`
- **Utility:** `battery_pct()`, `sleep_ms()`

ZRI reads its configuration from `zri_cfg.py` -- a plain Python dict that performers edit directly. This is where haptic pulse durations, button mappings, tilt axis and sensitivity, handedness, and encoding parameters are set. No special tools needed; just edit the file and reboot.

The full ZRI specification is in `.planning/Zancig_Routine_Interface.md`.

---

## Repository Structure

```
Zancig/
├── README.md
├── Watchy/
│   ├── docs/                    # Watchy-specific documentation
│   └── src/                     # Mirrors the watch filesystem
│       ├── main.py              # Launcher: menu, routine discovery, sleep
│       ├── zri.py               # ZRI implementation for Watchy V3
│       ├── zri_cfg.py           # ZRI config (haptic timing, tilt thresholds)
│       ├── zancig.py            # Low-level hardware driver
│       ├── zancig_cfg.py        # Hardware pin assignments, I2C addresses
│       ├── epd_driver.py        # E-paper display driver
│       ├── bma423.py            # Accelerometer driver
│       └── routines/            # Performance routines
│           ├── zri_test.py      # ZRI API exerciser
│           ├── tilt_trainer.py  # Accelerometer tilt input trainer
│           └── btn_check.py     # Button diagnostic
└── PageWalker/                  # Web tool for book test cribs
    ├── README.md
    ├── app.py                   # Flask server
    ├── walker.py                # Core page-mapping logic
    ├── templates/               # Web UI
    ├── texts/                   # Uploaded book texts
    └── data/                    # Project JSON files
```

The `src/` directory under `Watchy/` mirrors the device filesystem directly. To deploy, flash MicroPython to the device and copy the contents of `src/` to the watch. No build step or structural translation required.

---

## PageWalker

PageWalker is a companion web tool for building book test cribs. It maps a plain-text digital book (e.g., from Project Gutenberg) to physical page numbers by letting you walk through the book page-by-page with the physical copy in hand, marking where each page ends.

The output is a JSON file mapping every page number to its text, which you can then use to build crib sheets for performance.

See [`PageWalker/README.md`](PageWalker/README.md) for setup and usage.

---

## Design Philosophy

- **Stealth-first.** The device is dark and silent by default. Display and sound are opt-in per routine. Haptic is the primary output channel.
- **Performance resilience.** A failure during a show is catastrophic, not inconvenient. Code paths are kept simple. No databases, no network dependencies, no complex state machines.
- **Performer-modifiable.** Routines are plain `.py` files. Config is plain `.py` dicts. Timing values, haptic patterns, and thresholds are all tunable without recompiling or reflashing firmware.
- **No unnecessary abstraction.** Module-level functions, not classes. Fire-and-forget defaults, optional parameters for control. Three similar lines of code are better than a premature abstraction.
- **Device-agnostic routines.** All hardware interaction goes through ZRI. A routine written for Watchy should run on Thumby Color without changes, as long as it only uses capabilities both devices share.

---

## Getting Started

### Watchy V3

1. **Flash MicroPython** to your Watchy V3. The easiest method is the [Adafruit WebSerial ESPTool](https://adafruit.github.io/Adafruit_WebSerial_ESPTool/) in Chrome or Edge -- no install required. Erase the flash first, then flash a MicroPython build for ESP32-S3 with SPIRAM.
2. **Copy `Watchy/src/`** to the watch filesystem using `mpremote`, Thonny, or any MicroPython file transfer tool.
3. **Boot the watch.** `main.py` runs automatically, presenting a menu of available routines.
4. **Navigate:** top-right button (TR) cycles through menu items and launches the selected routine. Bottom-left (BL) long-press enters MicroPython mode for development.

---

## Contributing

Contributions are welcome -- new routines, platform ports, documentation improvements, and bug fixes.

Routines that duplicate the core functionality of actively sold commercial mentalism products will not be accepted into the main library at this time.

Please open an issue before beginning significant new work, to avoid duplication of effort.

---

## Attribution

Named after Julius and Agnes Zancig, Danish-American mentalists whose celebrated two-person telepathy act (late 1800s -- early 1900s) remains a foundational reference in the history of covert performance communication. Their methods, their discipline, and their respect for the audience remain the spirit behind this project.

---

## License

Project Zancig uses a split license:

**Platform code, HAL, and routines** -- licensed under the [GNU Lesser General Public License v3.0](LICENSE-CODE) (LGPL v3). You may use, modify, and distribute this code, including as part of a larger work, provided that modifications to the Zancig code itself are shared back under the same terms.

**Specification documents and documentation** (including this README) -- licensed under [Creative Commons Attribution-ShareAlike 4.0 International](LICENSE-DOCS) (CC BY-SA 4.0). You may freely use, adapt, and redistribute these materials provided appropriate credit is given and derivatives are shared under the same license.

Routine files are LGPL v3 as code. Performance descriptions and encoding logic documented in prose within a routine are CC BY-SA 4.0.

Contributions to the main repository are understood to be submitted under the applicable license for the component being contributed, as described above, unless explicitly stated otherwise.

On-device LGPL compliance for MicroPython platforms is satisfied by retaining the Zancig `.py` source files in editable form on the device, which is the default state of any MicroPython deployment.
