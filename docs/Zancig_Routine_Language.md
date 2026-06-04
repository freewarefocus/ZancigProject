# Zancig Routine Language (ZRL)

**Working name:** "ZancigPython" · **Status:** v0.2 — post-first-routine revision · **Substrate:** MicroPython

This is the language you write Zancig performance routines in. It is **not a new
language** — it is a deliberately narrow *subset* of MicroPython. Anything you
write that follows this guide runs unmodified on every MicroPython device (Watchy,
Thumby Color, …) with no build step. The restrictions exist for one reason: so the
same routine file can also be **mechanically translated to JavaScript** (Bangle.js /
Pebble) and, later, possibly C — without anyone hand-porting it.

> **The one rule that governs everything:** *if it can't be translated cleanly, it
> isn't in the language.* The linter and the transpiler are the same tool. If the
> transpiler accepts your routine, it's valid ZRL. If it rejects it, that rejection
> is your lint error.

---

## 1. The mental model

1. **A routine is pure logic.** It does input → computation → output and nothing else.
2. **Hardware does not exist for a routine.** Buttons, tilt, screen, motor — a routine
   never touches any of them. It only ever talks to `zri`. (See §7.)
3. **A routine asks for *meaning*, not mechanism.** It says "give me a digit" or "buzz
   short." *How* that happens — a button on Thumby, a tilt on Watchy, an ERM vs an LRA
   motor — is the performer's configured choice, resolved by ZRI. The routine is none
   the wiser.
4. **The routine never handles its own failures.** The runtime catches errors and
   recovers safely. You do not write `try/except`. (See §9.)
5. **Stay narrow.** If you find yourself reaching for a feature not listed in §4, stop —
   that's almost certainly a feature we deliberately left out (§5).

---

## 2. Anatomy of a routine

Every routine is a single `.py` file with exactly three things:

- a `REQUIRES` list (what the routine genuinely *cannot* run without),
- any helper functions you need,
- a `run()` function — the entry point the launcher calls.

```python
import zri

# Declare only capabilities that have NO substitute on a device.
# (Most I/O is substitutable and must NOT be listed here — see §8.)
REQUIRES = ['screen_text']

def run():
    zri.init()
    zri.haptic_ready()
    # ... your routine ...
    zri.done()
```

`import zri` is the **only** import you are allowed.

---

## 3. Quick reference

| You may use | You may **not** use |
|---|---|
| `def`, positional + simple default args, recursion | classes, `self`, inheritance |
| `if` / `elif` / `else`, `while`, `for … in` | generators / `yield` |
| `break`, `continue`, `return`, `pass` | `try` / `except` / `raise` *in a routine* |
| `int`, `float`, `bool`, `str`, `None`, `list`, `dict` | tuple literals (use a 2-element list) |
| arithmetic, comparisons, `and` / `or` / `not` | decorators, `lambda` |
| bitwise `^`, `&`, `\|` | bitwise `~`, `<<`, `>>` |
| augmented assignment (`+=`, `-=`, `*=`, `//=`, `%=`, `^=`, `&=`, `\|=`) | `**=`, `<<=`, `>>=` |
| f-strings with simple `{expr}` (see §4) | format specs (`{x:.2f}`), conversion flags (`{x!r}`) |
| `a, b = func()` (2- or 3-element unpacking) | starred / loop / nested unpacking |
| indexing, slicing, `in` | comprehensions |
| `x if cond else y` | `global` / `nonlocal`, `*args` / `**kwargs` |
| `len, range, abs, min, max, int, float, str, bool, round, sum` | any other builtin or stdlib |
| `list.append(value)` | other list methods (`.pop()`, `.sort()`, etc.) |
| `dict.get(key, default)` | other dict methods (`.keys()`, `.values()`, etc.) |
| `clamp()`, `lookup()` (provided — see §10) | `import` of anything but `zri` |
| `zri.*` (all hardware — see §7) | direct hardware access of any kind |

---

## 4. What the language includes

### Control flow
`if / elif / else`, `while`, `for x in range(...)`, `for x in some_list`, plus
`break`, `continue`, `return`, `pass`.

### Functions and recursion
Plain `def` with positional arguments and simple literal defaults. Recursion is
allowed and is the natural way to write search/solver logic:

```python
def best_score(board, depth):
    if depth == 0:
        return evaluate(board)
    # ... recurse ...
```

> **Recursion depth ceiling: keep it shallow (aim for ≤ ~30 frames).** MicroPython on
> ESP32, Espruino, and Pebble's XS all have modest stacks. If a routine might recurse
> deeply, rewrite it iteratively using a list as an explicit stack — the translation
> treats both identically, so this is purely an authoring choice.

### Data
`int`, `float`, `bool`, `str`, `None`, `list`, `dict`.

- **Lists** are your workhorse. A 2-D board is a flat list with `row * width + col`
  indexing — you do not need nested structures.
  Lists support `.append(value)` for building variable-length collections. No other
  list methods are allowed (`.pop()`, `.remove()`, `.insert()`, `.sort()`, `.extend()`
  are all deferred — see §6).
- **Dicts** are allowed and encouraged — they are your lookup tables and your
  memoisation (transposition) tables.
  Dicts support `.get(key, default)` for safe access; `lookup()` (§10) remains the
  recommended pattern for crash-proof access. No other dict methods are allowed.
  (`.keys()` is not needed — use `for key in my_dict` or `key in my_dict`.)
- **Strings** have no methods in v0.2. String methods (`.upper()`, `.lower()`,
  `.split()`, `.strip()`) are deferred to §6.
- **No tuple literals.** To return more than one value, return a 2-element list.
  However, **simple unpacking** of list returns is allowed (2 or 3 elements):

```python
def best_move(board):
    # ...
    return [col, score]

col, score = best_move(board)    # unpacking — cleaner than result[0]/result[1]
```

Only assignment-context unpacking is allowed. Loop unpacking (`for a, b in pairs`),
starred unpacking (`a, *rest = ...`), and nested unpacking are all excluded.

### Expressions
Arithmetic (`+`, `-`, `*`, `//`, `%`, `**`), comparisons, boolean `and` / `or` /
`not`, indexing and slicing, membership (`x in my_list`, `key in my_dict`), and the
ternary `value_if_true if cond else value_if_false`.

Bitwise `^` (XOR), `&` (AND), `|` (OR) are allowed — they are identical operators in
Python, JS, and C. Bitwise NOT (`~`) and shifts (`<<`, `>>`) are excluded due to
sign-extension subtleties across targets.

Augmented assignments: `x += 1` is equivalent to `x = x + 1`. Supported: `+=`, `-=`,
`*=`, `//=`, `%=`, `^=`, `&=`, `|=`. Excluded: `**=`, `<<=`, `>>=`.

### String interpolation
f-strings with simple expressions are allowed:

```python
label = f'PILE {i + 1} SIZE?'       # variable + arithmetic
result = f'{word} on page {page}'    # multiple interpolations
msg = f'Score: {compute(board)}'     # function call
```

**Allowed inside `{}`:** variables, arithmetic, function calls — anything the
transpiler can lift into a JS template literal or C `snprintf`.

**Not allowed:** format specs (`{x:.2f}`), conversion flags (`{x!r}`), nested or
complex expressions. If you need formatting beyond simple interpolation, build the
string with `+` and `str()`.

### Builtins
The **entire** allowed builtin set: `len`, `range`, `abs`, `min`, `max`, `int`,
`float`, `str`, `bool`, `round`, `sum`. Nothing else. No `import math` — if a routine
needs a maths helper that isn't here, that's a gap to raise (§12).

---

## 5. What the language excludes (and why)

These are left out specifically because they make clean translation hard or
unbounded:

- **Classes / inheritance** — routines are simple enough not to need them, and they
  balloon the translator.
- **Generators / `yield`** — no clean, cheap equivalent across all targets.
- **`try` / `except` / `raise` inside a routine** — error recovery belongs to the
  runtime, not the routine (§9). Raising an error is never how a routine should behave.
- **Decorators, `lambda`, comprehensions** — translatable in principle, but they widen
  the surface for no benefit to a (semi-)non-technical author. Deferred (§6).
- **`global` / `nonlocal`, `*args` / `**kwargs`, keyword-only args** — pass state
  explicitly through arguments instead.
- **Tuple literals** — replaced by 2-element lists (but unpacking is allowed — see §4).
- **The standard library** (except the handful of builtins in §4) — and **all imports
  except `import zri`**.
- **Any direct hardware access** — there is none to access; everything is `zri`.

---

## 6. Deferred — candidates for later versions

These are *not* in v0.2 but are reasonable to add if future routines show they're
worth it. They're listed separately so the decision stays visible:

- **Bitwise NOT (`~`) and shifts (`<<`, `>>`)** — sign-extension semantics differ
  between Python and JS/C. If a routine genuinely needs shifts, that's a gap to raise.
- **f-string format specs** (`{x:.2f}`) **and conversion flags** (`{x!r}`) — the
  format mini-language is large; simple `{expr}` covers routine needs.
- **Extended unpacking** — loop unpacking (`for a, b in pairs`), starred unpacking
  (`a, *rest = ...`), and nested unpacking are deferred.
- **List comprehensions** — a plain `for` loop does the same job for now.
- **`lambda`** — translatable to arrow functions; deferred for simplicity.
- **Additional list methods** — `.pop()` is a strong candidate if stack-like patterns
  emerge. `.sort()`, `.remove()`, `.insert()`, `.extend()` are deferred.
- **Additional dict methods** — `.keys()`, `.values()`, `.items()` are deferred.
  Use `for key in my_dict` or `key in my_dict` instead.
- **String methods** — `.upper()`, `.lower()`, `.split()`, `.strip()`, `.join()` are
  all translatable and may be promoted if string-heavy routines need them.

---

## 7. Hardware lives entirely behind ZRI

A routine reaches the device **only** through the `zri` module. This is what makes a
routine portable and what makes the translation small (the translator only has to map
`zri` calls plus pure logic; every device-specific detail is hand-ported once per
platform inside `zri` itself).

### The ZRI verb set

- **Lifecycle:** `init()`, `stealth()`, `done()`
- **Input:** `get_digit()`, `get_confirm()`, `wait_press()`
- **Haptic:** `haptic()`, `haptic_digit()`, `haptic_ready()`, `haptic_end()`, `haptic_nack()`
- **Display:** `show()`, `show_large()`, `show_page()`, `clear()`
- **Sound:** `tone()`, `melody()`, `volume()` *(capability-gated — check first, §8)*
- **Config:** `load_config()`, `save_config()`
- **Utility:** `battery_pct()`, `sleep_ms()`

### Named output is the default; raw output is an escape hatch

Prefer the **named** outputs (`haptic_digit`, `haptic_ready`, "short" / "long"
patterns). They are config-driven: the author states intent, and the performer's
`zri_cfg.py` decides exactly how each one feels. That separation — *author writes the
logic, performer tunes the feel* — is the whole point, and named outputs preserve it.

A raw call (e.g. an explicit pulse length) may be offered as an escape hatch, but it
still passes through ZRI and is still scaled by the performer's global feel settings,
so a routine can never fully bypass the performer's calibration.

---

## 8. Capabilities and the `REQUIRES` manifest

`REQUIRES` is a **module-level list literal** at the top of the file. The launcher
reads it *without running the routine*, so it can refuse to even list a routine on a
device that can't support it — meaning incompatibility is discovered while loading in
the study, never mid-performance. (The same literal is lifted into a manifest for the
JS/Pebble launchers automatically, so load-time filtering works identically there.)

### Declare only what has no substitute

This is the key principle. Most I/O is **substitutable** and must **not** be listed:

- "Get a number / digit / yes-no" — every device with any input can satisfy this via
  some configured method. **Not a requirement.**
- "Convey a small value back" (a digit, a yes/no) — works over haptic *or* screen *or*
  sound. **Not a requirement.**

A genuine requirement is something with **no fallback** on a device that lacks it:

| Capability | Means | Fails on |
|---|---|---|
| `screen_text` | must display readable text/words (e.g. a book-test reveal) | screenless devices |
| `sound` | must emit audible tones/melody | silent devices |

> Haptic output is assumed present on all Zancig devices (it is the primary covert
> channel), so it is a baseline guarantee, not something you declare.

For *optional* behaviour, query at runtime instead of requiring — adapt if it's there,
carry on if it isn't:

```python
if zri.CAPS.get('sound'):
    zri.tone(440, 200)
```

So: **`REQUIRES` = "won't run without this." `CAPS` = "use it if it happens to be here."**

---

## 9. Error handling — the routine does nothing

In a performance, the worst outcome is not a failed effect — a practised performer can
cover a failed effect. The worst outcome is a **visible anomaly**: a frozen screen, a
stray buzz, an error message. That is a tell, and possibly an exposure.

So error handling is the **runtime's** job, not yours:

- **Do not write `try` / `except` in a routine.** Let the runtime's top-level guard
  catch anything unexpected.
- On any uncaught error the runtime will: silence all output, return the device to its
  least-conspicuous state (idle / dark — it does **not** restart your routine), and log
  the error **to flash, never to the screen** so you can review it after practice.
- The translated JS/Pebble runtimes implement the *same* silent-recovery behaviour, so
  a routine that fails safely in MicroPython fails safely everywhere.

Your part is to **not crash in the first place** on edge cases that practice might not
surface — which §10 makes nearly automatic.

---

## 10. Standard helpers (always available, no import)

The runtime provides these to every routine so that graceful degradation isn't your
burden. They are available as bare names — you do not import them.

### `clamp(value, low, high)`
Returns `value` forced into the range `low..high`. Use it on anything coming from
input or arithmetic so an out-of-range value can never propagate.

### `lookup(table, key, default)`
A **total** dictionary lookup: returns `table[key]` if present, otherwise `default`.
Never raises. This is how lookups stay crash-proof on the page/word/index that the
performer never happened to test.

```python
page = clamp(page, 1, 99)               # never out of range
word = lookup(CRIB, page, "(none)")     # never throws
```

> **Make every lookup total.** Prefer `lookup(...)` over `table[key]`, and clamp indices
> before you use them. A clamped-or-defaulted result degrades into something the
> performer can still work with; an uncaught `KeyError` / `IndexError` aborts the beat.

---

## 11. Worked example

A simple reveal: the performer secretly enters a position (1–9) and the device reveals
the word they've pre-memorised for that position. Uses only documented ZRI verbs, the
two helpers, a dict lookup table, and f-string interpolation.

```python
import zri

# Must display a word, so it declares the one hard requirement it has.
REQUIRES = ['screen_text']

# The pre-memorised list, as a lookup table.
WORDS = {
    1: "anchor",
    2: "bridge",
    3: "candle",
    4: "dagger",
    5: "ember",
    6: "feather",
    7: "garden",
    8: "harbor",
    9: "ivory",
}

def run():
    zri.init()
    zri.haptic_ready()

    pos = zri.get_digit()              # ZRI resolves this via the performer's input
    pos = clamp(pos, 1, 9)             # never out of range
    word = lookup(WORDS, pos, "?")     # total lookup, never throws

    zri.show_large(word)
    zri.wait_press()
    zri.done()
```

And a small **compute** fragment, showing integer division, unpacking, and augmented
assignment:

```python
def split_tens(n):
    n = clamp(n, 0, 99)
    tens = n // 10        # integer division — use // , never /
    ones = n % 10         # safe: operands are non-negative (see semantics note)
    return [tens, ones]

t, o = split_tens(42)    # unpacking: t=4, o=2
total = 0
for d in digits:
    total += d            # augmented assignment
```

---

## 12. Semantics that bite *inside* legal code

These are behaviours that are valid syntax but differ between MicroPython and the
translation targets. The linter warns on them; learn them and they stop being a
problem:

- **Integer division uses `//`.** `/` always produces a float. (In JS, `//` becomes
  `Math.floor(a / b)`; `/` stays `/`.)
- **`//=` follows the same semantics as `//`** — `x //= 3` is equivalent to
  `x = x // 3` and produces an integer result.
- **Modulo on negatives differs.** In Python `-7 % 3 == 2`; in JS the raw operator
  gives `-1`. The translator emits a Python-semantics `%` helper, so you're safe — but
  the simplest habit is to keep `%` operands non-negative.
- **Do not rely on the truthiness of collections.** An empty list/dict is *falsy* in
  Python but *truthy* in JS. Write `if len(x) > 0:`, never `if x:` for a list or dict.
- **Null checks use `is None` / `is not None`,** not `==`.
- **Keep integers under 2^53.** On the JS side numbers are doubles; beyond that ints
  lose precision. A non-issue for this domain, but worth knowing.
- **Keep bitwise operands non-negative and under 2^32.** JS bitwise operators work on
  signed 32-bit integers. Negative or large operands produce different results across
  targets. For game-theory XOR folds and flag masking, single-digit values are fine.
- **Don't grow lists unboundedly.** `.append()` is for building finite collections
  (pile lists, move histories, result buffers). The runtime may enforce a cap. If a
  list might grow without limit, redesign the algorithm.
- **f-string interpolated values must be `int`, `float`, `str`, or `bool`.** Lists and
  dicts inside `{}` produce target-dependent output. Convert explicitly if needed:
  `f'count: {len(items)}'` (int) is fine; `f'data: {items}'` (list) is not.

---

## 13. Pre-flight checklist

Before loading a routine to practise:

- [ ] Only `import zri`; no other imports.
- [ ] `REQUIRES` lists only non-substitutable needs (§8).
- [ ] No `try` / `except`; no `raise`.
- [ ] No classes, generators, comprehensions, `lambda`, decorators.
- [ ] No tuple literals (use 2-element lists; unpacking the result is fine).
- [ ] Only the §4 builtins are used; only allowed type methods (`.append()`, `.get()`).
- [ ] f-strings use only simple `{expr}` — no format specs, no conversion flags.
- [ ] Every dict access uses `lookup(...)`; every index is `clamp`-ed or known-safe.
- [ ] `//` for integer division; `len(x) > 0` not `if x:`; `is None` for null checks.
- [ ] Bitwise operands are non-negative and under 2^32.

If the linter/transpiler accepts it, it's valid ZRL and it will run on every target.

---

## 14. This is a living spec — expect gaps

v0.2 was shaped by writing a real routine (Nim) against v0.1 and cataloguing the
friction. The additions — bitwise operators, `.append()`, f-strings, unpacking,
augmented assignment — each passed the same bar: zero or near-zero transpiler cost,
and a real routine couldn't be written cleanly without them.

When you hit something you genuinely need that isn't here, that's a **gap to fill**,
not a rule to quietly break — note it, and we decide whether it earns a place (and
whether it translates cleanly) before it goes in.

If a helper function is needed across multiple routines, the right path is to propose
it as a **runtime builtin** (like `clamp()` and `lookup()`) rather than a shared import.
The "only `import zri`" rule is a powerful simplifying constraint worth preserving.

Keeping the language small is a feature. Every addition is also work in the translator
and a new thing for an author to learn — so the bar for adding is "a real routine
couldn't be written cleanly without it."
