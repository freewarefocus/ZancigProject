# Zancig Routine Interface (ZRI) Specification

## Purpose

ZRI is a device-agnostic API for Zancig routines. Each device ships its own `zri.py` implementing this spec. Routines express intent ("get a digit 1-6", "play short-long-short") and the device handles the how.

## Design Principles

- **Module-level functions** -- no classes, minimal RAM on MicroPython
- **Each device ships its own `zri.py`** -- no dispatcher, no extra import
- **Blocking I/O** -- `get_digit()`, `haptic()` block until complete
- **Graceful degradation** -- every function returns False/None if capability absent
- **Routines import only `zri`** -- never device-specific modules
- **Dedicated appliance** -- Zancig turns a general-purpose device into a dedicated routine machine. The launcher facilitates routine selection (long press to launch, safe against accidental activation) then gets out of the way. Once running, the routine drives the bus.
- **Performance resilience** -- routines are bulletproof during performance. No accidental exit path, no stray button that kills the routine mid-show. Input functions only respond to the confirm button (short=positive, long=negative). The routine owns its lifecycle: it runs until it decides it's done, then hands back to Zancig or enters deep sleep. An interrupted performance is a disaster; a post-show reboot is a minor inconvenience.

## Capabilities System

`zri.CAPS` is a dict populated by `init()`. It is the contract between what a routine wants and what a device can do. Routines check CAPS before using optional features and degrade gracefully when a capability is absent.

CAPS is intentionally extensible. Adding a new output modality to Zancig — a servo controller, an IR blaster, a relay board, a remote thumper — follows the same pattern every time: add a CAPS key, add thin API functions to ZRI, implement them in the device's `zri.py`. Routines that don't use the new capability are unchanged. Devices that don't support it just report `False`.

Current capabilities:

| Key | Type | Example (Watchy) | Example (Thumby Color) |
|---|---|---|---|
| `haptic` | bool | True | True |
| `screen` | bool | True | True |
| `brightness` | bool | False | True |
| `sound` | bool | False | True |
| `accel` | bool | True | False |
| `battery` | bool | True | True |
| `data` | bool | True | True |
| `device` | str | `'watchy'` | `'thumby_color'` |
| `input_method` | str | `'tilt'` | `'dpad'` |

Routines check `CAPS` before using optional features.

## API Reference

### Lifecycle

#### `init() -> dict`
Prepare ZRI for use. Safe to call multiple times (idempotent).
Returns the `CAPS` dict for convenience — equivalent to accessing `zri.CAPS` directly.
- **First call** (launcher at boot): hardware init, load config, populate `CAPS`
- **Every call**: (re)calibrate input baseline (e.g. accelerometer neutral on Watchy)

Routines call `init()` at their start. This captures the performer's current
position as the input reference point. The routine doesn't know or care what
device-specific setup happens inside -- it just means "I'm ready, prepare input."

Every call resets `configure()` overrides (centre, base) to the config baseline.

#### `stealth()`
Go dark immediately. Display off, backlight off, all visual output suppressed.
Use this mid-routine when the display phase is over and the performance phase
begins — e.g. after showing a crib sheet, before the haptic-only portion.

Haptic-only routines can call `stealth()` right after `init()` to ensure the
screen never activates at all.

Any subsequent display call (`show()`, `show_large()`, etc.) automatically
exits stealth — no explicit "unstealth" needed.

#### `done()`
Routine is finished. Calls `stealth()` internally, then waits for any button
press before returning to the launcher menu. The device just sits dark and idle
until the performer is ready.

Typical routine lifecycle: `init()` -> do work -> `done()` -> back to menu.

### Per-Routine Configuration

#### `configure(centre=None, base=None)`
Override input centre and/or haptic encoding base for this routine. Call after `init()`. Omit a kwarg to keep the device default.

- `centre`: starting digit for jog input (overrides `default_centre` from config)
- `base`: haptic encoding divisor (overrides `base` from config). `longs = n // base`, `shorts = n % base`

**Precedence:** `configure()` override > `zri_cfg.py` value > built-in default.

**Soft semantics:** `configure()` never raises. On a device without haptic, `base` is stored but never consumed. On a device without tilt input, `centre` is stored but never read. This lets routines call `configure()` unconditionally without checking CAPS.

**Reset:** `init()` resets both values to the config baseline, clearing any previous routine's override. This happens automatically when the next routine calls `init()`.

```python
zri.init()
zri.configure(centre=3, base=3)   # base-3 encoding, jog starts at 3
n = zri.get_digit(1, 6)           # jog starts at 3
zri.haptic_digit(n)               # encoded with base 3
```

### Input

#### `get_digit(lo=1, hi=9, prompt=None, format_fn=None) -> int`
Full input cycle: device-appropriate jog + confirm button.
- `lo`, `hi`: digit range (inclusive)
- `prompt`: optional title string for display
- `format_fn(n) -> str`: optional, called with current digit to show extra info
- **No built-in haptic echo** -- routine handles its own echo after return
- Input baseline is stable across calls (set by `init()`)
- Always returns a confirmed digit (int) -- no exit path

Behavior (device handles the how):
1. Shows digit selection UI
2. Jog input changes digit (tilt on Watchy, D-pad on Thumby, etc.)
3. Tick_up haptic on increment, tick_down on decrement
4. Short press = confirm (returns digit)
5. Long press = NACK + reset to centre

#### `get_confirm(prompt=None) -> bool`
Short press = yes (True), long press = no (False).
No exit path -- always returns a definite answer.

#### `wait_press() -> str`
Block until any button pressed. Returns button name.

### Haptic Output

#### `haptic(pattern, timings=None) -> bool`
Play a pattern string with auto-gaps between elements.
- Pattern chars: `S` = short, `L` = long, `U` = tick_up, `D` = tick_down
- `timings`: optional dict overriding default `short_ms`, `long_ms`, etc.
- Returns True on success, False if no haptic capability

Examples:
```python
zri.haptic('SLS')       # short-long-short
zri.haptic('LLS', {'long_ms': 500})  # custom timing
```

#### `haptic_digit(n) -> bool`
Standard encoding: `longs = n // base`, `shorts = n % base`.
Base defaults to 4 (from config), overridable via `configure(base=N)`.

| n | Pattern | Pulses |
|---|---------|--------|
| 1 | S | * |
| 2 | SS | ** |
| 3 | SSS | *** |
| 4 | L | - |
| 5 | LS | -* |
| 6 | LSS | -** |
| 7 | LSSS | -*** |
| 8 | LL | -- |
| 9 | LLS | --* |

#### `haptic_gap(ms=None)`
Pause between digit groups. Default: `digit_gap_ms` from config.

#### `haptic_ready()`
Signal: two longs (`LL`).

#### `haptic_end()`
Signal: three longs (`LLL`).

#### `haptic_nack()`
Signal: three fast buzzes (reject/reset).

### Sound

Sound is off by default (stealth). Routines must explicitly call sound functions — like display, calling a sound function implicitly breaks stealth for that modality. `stealth()` and `done()` silence everything.

Not every device has useful sound hardware. Check `CAPS['sound']` before use. On devices without a speaker or with an inadequate piezo, sound functions return False silently.

#### `tone(freq_hz, duration_ms) -> bool`
Play a single tone. The atomic sound unit. Blocks for the duration.
- `freq_hz`: frequency in Hz (device clamps to its playable range)
- `duration_ms`: tone length in milliseconds
- Returns True if sound hardware available

#### `melody(notes) -> bool`
Play a sequence of tones. Blocks until complete.
- `notes`: list of `(freq_hz, duration_ms)` tuples. Use `0` freq for rests/silences
- Returns True if sound hardware available

```python
# Creepy music box — simple descending figure
zri.melody([
    (880, 300), (0, 100),    # A5, rest
    (784, 300), (0, 100),    # G5, rest
    (659, 600), (0, 200),    # E5 held, rest
    (523, 800),              # C5 long
])
```

#### `volume(level) -> bool`
Set sound volume 0-100. Device maps to whatever control it has (PWM duty cycle, DAC level, etc.). Returns False if no sound capability.

### Display

Display calls auto-manage stealth transitions. Routines never control backlights, color schemes, or refresh strategies directly — ZRI bakes in the right behavior per device:

- **Any display call** (`show()`, `show_large()`, `refresh()`) **auto-unstealths** — on Thumby Color this means backlight on at the configured dim level; on Watchy this means a partial screen update (no full black-white-black flash)
- **`stealth()` and `done()`** go dark — backlight off, display cleared/powered down
- **Color scheme is baked in per device** — Watchy uses white-on-black (dark rectangle on wrist, minimal flash), Thumby Color uses light-on-dark with dim backlight. Routines never specify colors
- **Haptic-only routines** that never call display functions get a dark screen throughout — no action needed

#### `show(lines, title=None) -> bool`
Display a list of strings. Auto-sized (scale 2), centered horizontally.
- `lines`: list of strings (max 8, truncated to 12 chars)
- `title`: optional header above a divider line
- Returns True if screen available

#### `show_large(lines, scale=None, overflow='scale') -> bool`
Display 1-4 items as large as the screen allows, centered both horizontally and vertically. Accepts either a single string or a list of strings.

**Scale behavior:**
- **`scale=None` (default):** auto-scales — ZRI calculates the largest font scale that fits all lines on the current device's screen
- **`scale=N`:** forces a specific scale. When content is too wide for the screen at the forced scale, the `overflow` parameter controls what happens

**Overflow modes** (only relevant when `scale` is forced or content is too wide):
- **`'scale'` (default):** shrink to fit. Finds the largest scale where all content fits. This is the fire-and-forget mode — content is always complete, ZRI always finds a way. When `scale` is not forced, this is the only behavior (auto-scale never truncates or wraps)
- **`'truncate'`:** clip lines to whatever fits the screen width at the requested scale. For mentalism this is often ideal — the first 5-6 characters of a word give it away, and a near-miss read ("I'm getting... CHRYSA... CHRYSANTHEMUM?") can play better than nailing it instantly
- **`'wrap'`:** word-wrap long lines onto the next row, maintaining the forced scale. Consumes additional vertical lines. Best when the full text matters and the performer has time to read — e.g. a sentence fragment, an address, a full title

Line count behavior (auto-scale):
- 1 line: fills the screen (digits, short words)
- 2 lines: each gets roughly half the screen height — ideal for book tests, two-word reveals
- 3-4 lines: still significantly larger than `show()` default — ideal for a magic square row split across lines, or short data groups

The routine author never specifies pixel coordinates. ZRI handles the device-specific layout math so the same call works on both 128x128 IPS and 200x200 e-paper.

Examples:
```python
# Fire-and-forget -- auto-scale handles everything
zri.show_large('42')                        # single number, huge
zri.show_large(['GARDEN', 'TEMPLE'])        # book test, two big words
zri.show_large(['12   7', '24   1'])        # magic square row, split for readability

# Forced scale with overflow modes
zri.show_large(['CHRYSANTHEMUM'], scale=4)                    # default: shrinks to fit
zri.show_large(['CHRYSANTHEMUM'], scale=4, overflow='truncate')  # "CHRYSA" at scale 4
zri.show_large(['CHRYSANTHEMUM'], scale=4, overflow='wrap')      # "CHRYSAN-" / "THEMUM"

# Bad-eyes friendly -- force big, let ZRI handle overflow
zri.show_large(['GARDEN', 'TEMPLE'], scale=5)                 # big text, scales if needed
zri.show_large(['GARDEN', 'TEMPLE'], scale=5, overflow='truncate')  # big, clips if needed
```

#### `clear() -> bool`
Clear the display.

#### `show_at(text, x, y, scale=1) -> bool`
Draw text at specific pixel coordinates. Enables positional placement for:
- Small data overlaid on a cover screen
- Multi-zone layouts
- Crib sheets with custom formatting

Does not trigger a screen refresh — call `refresh()` after batching multiple `show_at()` calls.

#### `show_page(lines, page=0, per_page=8, title=None) -> tuple(bool, int)`
Paginated display for longer lists. Returns `(success, total_pages)`.
- `lines`: full list of strings
- `page`: zero-indexed page number to display
- `per_page`: lines per page (default 8, fits scale-2 text on most screens)
- `title`: optional header (does not count toward `per_page`)

Routine handles page navigation via `get_digit()` or button input. This function only renders the requested page.

#### `set_font_scale(scale) -> bool`
Set default font scale for subsequent `show()` and `show_at()` calls.
- Scale 1 = ~25 lines on Watchy e-paper, small but readable at close range
- Scale 2 = ~8 lines (current default), comfortable reading distance
- Returns True if screen available, False otherwise

#### `draw_rect(x, y, w, h, fill=False) -> bool`
Basic rectangle drawing for dividers, borders, and highlights.
- Coordinates in pixels from top-left origin
- `fill=True` draws a filled rectangle; `fill=False` draws outline only
- Does not trigger a screen refresh — call `refresh()` after batching.

#### `refresh() -> bool`
Explicitly push framebuffer to display. Allows batching multiple `show_at()` / `draw_rect()` calls before a single screen update. This is important for e-paper (Watchy) where refreshes are slow and visually conspicuous — batch drawing operations and refresh once.

For IPS displays (Thumby Color), refresh is near-instant but batching is still good practice.

#### `brightness(level) -> bool`
Set screen brightness 0-100.
- Relevant for IPS displays (Thumby Color) — controls backlight intensity
- E-paper (Watchy) ignores this call (returns False)
- Useful for covert glancing: dim the screen so only the performer at close range can read it

### Config

#### `load_config(name, defaults=None) -> dict`
Load `/routines/{name}_cfg.py`, merged with defaults. Delegates to device framework.

#### `save_config(name, data)`
Write config dict to `/routines/{name}_cfg.py`.

### Data

Pipe-delimited `.dat` files in `/data/` on device. UTF-8, `#` comment lines. One key-value pair per line, separated by `|`. Values may be any length (single word, phrase, short sentence). Shared across routines — the same book crib can serve multiple routines.

#### File format

```
# Book: Dr Jekyll & Mr Hyde (Dover Thrift Edition)
# Source: PageWalker export
#
1|that they said nothing
2|stumping along eastward
3|the whole business looked
```

#### `load_data(name) -> dict`
Load entire `/data/{name}.dat` into a dict. Keys and values are strings. Returns empty dict if file not found.

For data that fits in RAM (up to ~500 entries on ESP32). Fire-and-forget — load once at routine start, look up by key thereafter.

```python
crib = zri.load_data('jekyll_hyde')
text = lookup(crib, str(page), '???')
zri.show_large(text)
```

#### `query_data(name, key) -> str | None`
Stream-search a `.dat` file for a single key without loading the whole file. Returns the value string, or None if not found.

For data too large for RAM (365+ entries). Linear scan: ~1-3 seconds for a 36,500-line file on ESP32. Acceptable for a single mid-performance lookup.

```python
fact = zri.query_data('date_facts', f'{month}/{day}')
if fact is None:
    fact = 'Nothing notable'
zri.show_large(fact)
```

#### Sizing guidance

| Size | Entries | Approach | Example |
|---|---|---|---|
| Tiny | <50 | Inline dict in routine | 9-word list, card positions |
| Small-Medium | 50-500 | `load_data()` | Book test (54pp), full deck (52) |
| Large | 500+ | `query_data()` | Date facts (365-36,500 entries) |

### Utility

#### `battery_pct() -> int | None`
Returns 0-100, or None if unavailable.

#### `sleep_ms(ms)`
Platform-appropriate sleep.

## Haptic Pattern Language

Characters:
- `S` -- short pulse (default 120ms)
- `L` -- long pulse (default 380ms)
- `U` -- tick_up pulse (default 80ms, increment feedback)
- `D` -- tick_down pulse (default 120ms, decrement feedback)

Gaps are auto-inserted between consecutive characters (default 200ms).

### Digit Encoding (Standard)
`longs = n // base`, `shorts = n % base`. Default base is 4, configurable via `zri_cfg.py` or `configure(base=N)`. Used by `haptic_digit()`.

### Signal Patterns
- **Ready**: `LL` (two longs)
- **End**: `LLL` (three longs)
- **NACK**: three 70ms buzzes with 100ms gaps (special, not pattern-based)

## Configuration

### `zri_cfg.py` (device-level)

```python
config = {
    'device': 'watchy',
    'short_ms': 120, 'long_ms': 380, 'tick_up_ms': 80, 'tick_down_ms': 120, 'gap_ms': 200,
    'digit_gap_ms': 650, 'move_gap_ms': 1100,
    'tilt_axis': 'y', 'tilt_invert': False,
    'tilt_threshold': 300, 'tick_interval_ms': 800,
    'confirm_btn': 'TL',
    'default_centre': 5,
    'base': 4,                   # haptic encoding base (longs=n//base, shorts=n%base)
}
```

### Routine configs
Routines use `zri.load_config()` / `zri.save_config()` for their own settings.
Device-level timings live in `zri_cfg.py`, not in routine configs.

## Routine Authoring Guide

### Adaptive routine (using CAPS)

```python
import zri

def run():
    caps = zri.init()
    rich = caps['screen']
    # ... adapt behavior based on device capabilities
```

### Minimal routine

```python
import zri

DEFAULTS = {'range_lo': 1, 'range_hi': 6}

def run():
    zri.init()
    cfg = zri.load_config('my_routine', DEFAULTS)
    lo, hi = cfg['range_lo'], cfg['range_hi']

    n = zri.get_digit(lo, hi, prompt="PICK")
    zri.haptic_digit(n)
    zri.show([f"Got: {n}"])
    zri.sleep_ms(1000)

    zri.done()  # dark screen, wait for press, back to menu
```

### Rules
1. Import only `zri` -- never device modules
2. Define `run()` as entry point
3. Call `zri.init()` at the top of `run()` (prepares input for this session)
4. Call `zri.done()` when finished (stealth idle, button press returns to menu)
5. Check `zri.CAPS` before using optional features
6. Never provide a mid-routine exit path -- input functions have no exit, only confirm and redo. An accidental exit mid-performance is far worse than needing a reboot after

### Display as Secondary Output

The screen is a secondary covert channel — not just for dev mode. Routines can use `show()`, `show_at()`, and `show_page()` to display crib sheets, lookup tables, or cover screens the performer can glance at during performance.

Guidelines:
- **Check `zri.CAPS['screen']`** before any display call (always True on current devices, but future headless thumper devices may lack a screen)
- **Check `zri.CAPS['brightness']`** and call `zri.brightness()` to dim IPS screens for covert use
- **Batch draw calls** with `show_at()` / `draw_rect()` and call `refresh()` once — especially important on e-paper where each refresh is slow and visible
- **Keep cover screens innocuous** — a watch face, a simple list, a blank screen. Nothing that looks like "computing" if glimpsed by an audience member
- **E-paper advantage:** Watchy's e-paper retains its image at zero power with no backlight glow — ideal for static crib sheets that the performer sets before the show begins

## Thumby Color Reference (Skeletal)

A Thumby Color `zri.py` would:
- `init()`: call `engine_main` import, set CAPS with `accel: False`, `input_method: 'dpad'`
- `get_digit()`: use D-pad buttons instead of tilt
- `haptic()`: use `engine_io.rumble()` with timed on/off
- `show()`: render to RGB screen via engine display API
- `battery_pct()`: map `engine_io.battery_level()` float to 0-100

## Migration Guide (zancig -> zri)

| Old (zancig) | New (zri) |
|---|---|
| `import zancig` | `import zri` |
| `zancig.init()` | `zri.init()` (launcher + each routine) |
| `return` from `run()` | `zri.done()` (stealth idle, then back to menu) |
| `zancig.send_digit(n)` | `zri.haptic_digit(n)` |
| `zancig.send_ready()` | `zri.haptic_ready()` |
| `zancig.send_end()` | `zri.haptic_end()` |
| `zancig.send_nack()` | `zri.haptic_nack()` |
| `zancig.buzz(ms, gap)` | `zri.haptic('S', {'short_ms': ms, 'gap_ms': gap})` |
| `zancig.read_digit(...)` | `zri.get_digit(...)` |
| `zancig.wait_button(name)` | `zri.wait_press()` |
| `zancig.display_word_list(...)` | `zri.show(lines, title)` |
| `zancig.display_number_large(n)` | `zri.show_large(n)` |
| `zancig.display_clear(); ...show()` | `zri.clear()` |
| `zancig.load_config(...)` | `zri.load_config(...)` |
| `zancig.battery_percent()` | `zri.battery_pct()` |
| `time.sleep_ms(ms)` | `zri.sleep_ms(ms)` |
