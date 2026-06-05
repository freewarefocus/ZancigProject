"""
crib.py  -  Crib extraction logic for PageWalker

Extracts memorable words from each mapped page using configurable rule presets.
No Flask dependencies — pure logic module.
"""

import re
import string


# ---------------------------------------------------------------------------
# Stop words (~150 common English words)
# ---------------------------------------------------------------------------

STOP_WORDS = frozenset("""
a about above after again against all am an and any are as at be because been
before being below between both but by can could did do does doing down during
each few for from further get got had has have having he her here hers herself
him himself his how i if in into is it its itself just let like me might more
most must my myself no nor not now of off on once only or other our ours
ourselves out over own past same shall she should so some still such take than
that the their theirs them themselves then there these they this those through
to too under until up upon us very was we were what when where which while who
whom why will with would you your yours yourself yourselves
a about after all also an and any are as at back be because been before being
between both but by came can come could day did do does each even find first
for from get give go going good great had has have he her here him his how
i if in into is it its just know last let life like little long look made
make man many may me might more most much must my never new next no not
now of off often old on one only or other our out over own part people
place point right said same say see she should show side since so some
something sometimes still such take tell than that the them then there
these they thing think this those though through time to too two under
up us use very want was way we well were what when where which while
who will with without work world would year yet you
""".split())


# ---------------------------------------------------------------------------
# Word cleaning
# ---------------------------------------------------------------------------

def _clean_word(word):
    """Strip all non-alphanumeric chars from edges, keep apostrophes inside."""
    # Strip anything that isn't a letter or digit from both ends
    word = re.sub(r"^[^a-zA-Z0-9]+", "", word)
    word = re.sub(r"[^a-zA-Z0-9]+$", "", word)
    return word


def _extract_words(text):
    """Split text into cleaned non-empty words."""
    return [w for w in (_clean_word(w) for w in text.split()) if w]


# ---------------------------------------------------------------------------
# Rule functions
# ---------------------------------------------------------------------------

def _rule_long_word(text, knobs):
    """First word with min_chars+ characters, then fallbacks."""
    min_chars = knobs.get("min_chars", 6)
    max_fallbacks = knobs.get("max_fallbacks", 3)
    words = _extract_words(text)

    primary = None
    primary_idx = -1
    for i, w in enumerate(words):
        if len(w) >= min_chars:
            primary = w
            primary_idx = i
            break

    if primary is None:
        # Fallback: longest word on the page
        if words:
            longest = max(words, key=len)
            return [longest]
        return []

    result = [primary]
    # Fallbacks: next qualifying words after primary
    count = 0
    for w in words[primary_idx + 1:]:
        if count >= max_fallbacks:
            break
        if len(w) >= min_chars:
            result.append(w)
            count += 1

    return result


def _rule_first_word(text, knobs):
    """First word of the page, plus fallbacks."""
    max_fallbacks = knobs.get("max_fallbacks", 3)
    words = _extract_words(text)

    if not words:
        return []

    result = [words[0]]
    for w in words[1:1 + max_fallbacks]:
        result.append(w)

    return result


def _rule_first_uncommon(text, knobs):
    """First word not in STOP_WORDS with min_chars+ characters."""
    min_chars = knobs.get("min_chars", 4)
    max_fallbacks = knobs.get("max_fallbacks", 3)
    words = _extract_words(text)

    primary = None
    primary_idx = -1
    for i, w in enumerate(words):
        if len(w) >= min_chars and w.lower() not in STOP_WORDS:
            primary = w
            primary_idx = i
            break

    if primary is None:
        # Fallback: first word not in stop words regardless of length
        for i, w in enumerate(words):
            if w.lower() not in STOP_WORDS:
                return [w]
        # Everything is a stop word — just return first word
        return [words[0]] if words else []

    result = [primary]
    count = 0
    for w in words[primary_idx + 1:]:
        if count >= max_fallbacks:
            break
        if len(w) >= min_chars and w.lower() not in STOP_WORDS:
            result.append(w)
            count += 1

    return result


def _rule_last_word(text, knobs):
    """Last word of the page, fallbacks working backwards."""
    max_fallbacks = knobs.get("max_fallbacks", 3)
    words = _extract_words(text)

    if not words:
        return []

    result = [words[-1]]
    # Work backwards for fallbacks
    for w in reversed(words[max(-len(words), -1 - max_fallbacks):-1]):
        result.append(w)

    return result


# ---------------------------------------------------------------------------
# Preset registry
# ---------------------------------------------------------------------------

PRESETS = {
    "long_word": _rule_long_word,
    "first_word": _rule_first_word,
    "first_uncommon": _rule_first_uncommon,
    "last_word": _rule_last_word,
}

PRESET_SCHEMAS = [
    {
        "name": "long_word",
        "label": "Long word",
        "description": "First word with N+ characters, scanning from the top of the page",
        "knobs": {
            "min_chars": {"type": "int", "default": 6, "min": 3, "max": 12},
            "max_fallbacks": {"type": "int", "default": 3, "min": 0, "max": 10},
        },
    },
    {
        "name": "first_word",
        "label": "First word",
        "description": "First word of the page, simple and fast",
        "knobs": {
            "max_fallbacks": {"type": "int", "default": 3, "min": 0, "max": 10},
        },
    },
    {
        "name": "first_uncommon",
        "label": "First uncommon word",
        "description": "First word not in the common-words list, with N+ characters",
        "knobs": {
            "min_chars": {"type": "int", "default": 4, "min": 3, "max": 12},
            "max_fallbacks": {"type": "int", "default": 3, "min": 0, "max": 10},
        },
    },
    {
        "name": "last_word",
        "label": "Last word",
        "description": "Last word of the page, fallbacks working backwards",
        "knobs": {
            "max_fallbacks": {"type": "int", "default": 3, "min": 0, "max": 10},
        },
    },
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_rule(text, rule, knobs):
    """Extract crib words from a single page's text using the named rule."""
    fn = PRESETS.get(rule)
    if fn is None:
        raise ValueError(f"Unknown rule: {rule}")
    return fn(text, knobs)


def generate_crib(project, rule, knobs):
    """Generate crib for all mapped pages. Preserves entries with override=True."""
    existing = project.crib.get("entries", {})

    entries = {}
    for pg in sorted(project.pages.keys()):
        pg_key = str(pg)

        # Preserve manual overrides
        if pg_key in existing and existing[pg_key].get("override"):
            entries[pg_key] = existing[pg_key]
            continue

        page_data = project.get_page_text(pg)
        if page_data is None:
            continue

        words = apply_rule(page_data["text"], rule, knobs)
        entries[pg_key] = {"words": words, "override": False}

    project.crib = {
        "rule": rule,
        "knobs": knobs,
        "entries": entries,
    }
    return project.crib


def export_crib_dat(project):
    """Render crib as a .dat string for device consumption."""
    crib = project.crib
    if not crib or not crib.get("entries"):
        return ""

    rule = crib.get("rule", "unknown")
    knobs = crib.get("knobs", {})
    knobs_str = ", ".join(f"{k}={v}" for k, v in knobs.items())

    lines = [
        f"# {project.title}",
        "# Source: PageWalker crib builder",
        f"# Rule: {rule} ({knobs_str})" if knobs_str else f"# Rule: {rule}",
        "#",
    ]

    for pg_key in sorted(crib["entries"].keys(), key=int):
        entry = crib["entries"][pg_key]
        words = entry.get("words", [])
        if words:
            words_str = ";".join(w.lower() for w in words)
            lines.append(f"{pg_key}|{words_str}")

    return "\n".join(lines) + "\n"
