# PageWalker

Sequential exact-boundary book mapper. Maps plain-text books to physical page numbers so you can build page-level cribs for book tests.

## Book Test Crib Generator

PageWalker is a crib generator for book tests. It takes any printed book you have the full text for and maps words precisely to each physical page, then extracts crib entries automatically using configurable rules.

The problem it solves: a digital text file (e.g., from Project Gutenberg) has no page breaks. PageWalker lets you walk through the book page-by-page with the physical copy in hand, marking where each page ends in the digital text. Once mapped, the built-in crib builder extracts memorable words per page and exports a device-ready `.dat` file.

Works especially well with cheap **Dover Thrift Editions** and other public-domain printings where the text is freely available on Gutenberg.

## Setup

```
pip install flask werkzeug
cd PageWalker
python app.py
```

Open `http://localhost:5001` in your browser.

## How It Works

### 1. Create a Project

From the home page, upload a `.txt` file (Gutenberg plain-text works best) and set the page range of your physical book. Check "Chapters always start on a new page" if your edition starts each chapter on a fresh page — PageWalker will auto-detect chapter boundaries during the walk.

### 2. Walk the Book

Open your physical book to page 1. For each page:

1. **Type a few words** from near the end of the physical page into the search box. PageWalker fuzzy-matches against the digital text and shows candidate words around your match.
2. **Press a digit (0-9)** to pick the last word on the physical page. This sets the exact boundary.
3. PageWalker advances to the next page. Repeat.

The search is forgiving — it normalizes punctuation and case, so you don't need exact transcription.

### 3. Chapter Auto-Detection

If enabled, PageWalker detects when a chapter heading falls within the current page's zone. When this happens, it suggests the boundary just before the heading. Press **Enter** to accept, or type in the search box to override.

### 4. Going Back

Press **b** or **Backspace** to go back one page and re-mark it. Going back invalidates all pages from that point forward (since each page's start depends on the previous page's end). If more than 5 pages would be invalidated, you'll get a confirmation prompt.

### 5. Editing Markers

Click **Markers** to see all mapped page boundaries in a table. You can click **Edit** on any individual page to re-search and re-pick its boundary without invalidating subsequent pages. Use this for small corrections where the overall flow is still correct.

### 6. Lookup

The walk page includes a Lookup section at the bottom:
- **Page #** — Enter a page number to see the full mapped text for that page.
- **Find phrase** — Search for any phrase to find which page it falls on.

### 7. Crib Builder

Once the walk is complete, the crib builder extracts memorable words from each mapped page. Access it via the link on the walk-complete screen or the Markers page, or directly at `/project/<slug>/crib`.

#### Preset Rules

| Preset | Description |
|---|---|
| `first_word` | First word of the page, simple and fast |
| `long_word` | First word with N+ characters, scanning from the top of the page |
| `first_uncommon` | First word not in the common-words list, with N+ characters |
| `last_word` | Last word of the page, fallbacks working backwards |

#### Knobs

Each rule exposes tunable knobs:

- **`min_chars`** — Minimum character length for a word to qualify. Default: 6 for `long_word`, 4 for `first_uncommon`.
- **`max_fallbacks`** — Number of additional qualifying words to include after the primary. Default: 3 (all rules).

#### Manual Overrides

Click any page's entry to edit its words manually. Overridden pages are flagged and preserved when you regenerate with a different rule or knobs. Click **Reset** to revert a page to the rule-generated words.

#### Exporting

Click **Export .dat** to download the crib as a device-ready `.dat` file. The file is also available at `GET /api/<slug>/crib/export.dat`.

## .dat Output Format

The `.dat` file is the primary output of PageWalker — a compact crib file designed for on-device lookup via ZRI `query_data()`. Each line maps a page number to one or more cue words extracted by the crib builder.

```
# The Strange Case of Dr Jekyll and Mr Hyde
# Source: PageWalker crib builder
# Rule: long_word (min_chars=6, max_fallbacks=3)
#
1|utterson;lawyer;rugged;countenance
2|stumping;eastward;curious
3|forward;haunted;singular
```

### Structure

- Lines starting with `#` are comments (ignored by `query_data()`).
- Data lines use pipe-delimited `key|value` format: `page_number|word1;word2;word3`.
- Words are lowercased and semicolon-separated. The first word is the primary cue; the rest are fallbacks in case the primary isn't distinctive enough.
- The file is plain text, typically under 2 KB — small enough for any microcontroller's filesystem.

### On-device usage

A Zancig routine loads the crib with ZRI's streaming search, so the full file never needs to sit in RAM:

```python
import zri

zri.init()
page = zri.get_digit()          # performer enters a page number
words = zri.query_data("jekyll-hyde", str(page))
if words:
    cues = words.split(";")
    zri.haptic_digit(len(cues[0]))   # buzz the word length
    zri.show(cues[0])                # or display the cue word
```

`query_data(name, key)` streams through the `.dat` file line-by-line, matching the key before the pipe. It returns only the value portion (everything after `|`), so the routine parses the semicolons itself.

### Why .dat over JSON

| | `.dat` | `.json` |
|---|---|---|
| **Size** | ~1-2 KB | ~5-15 KB |
| **RAM** | Zero — streamed line-by-line | Full parse into dict |
| **Lookup** | `query_data()` — O(n) scan, no allocation | `load_data()` — loads entire file |
| **Use case** | On-device routines (primary) | PageWalker internal state, custom tooling |

For microcontrollers with limited RAM, the `.dat` format is the only practical option. The JSON project file (`data/{slug}.json`) is PageWalker's internal save format, not intended for device deployment.

## JSON Project File (internal)

PageWalker saves walk state to `data/{slug}.json`. This is the working file that tracks page boundaries during the walk — not an output format for devices.

<details>
<summary>Schema reference</summary>

```json
{
  "title": "The Strange Case of Dr Jekyll and Mr Hyde",
  "slug": "the-strange-case-of-dr-jekyll-and-mr-hyde",
  "text_path": "texts/the-strange-case-of-dr-jekyll-and-mr-hyde.txt",
  "first_page": 1,
  "last_page": 54,
  "current_page": 55,
  "chapters_new_page": true,
  "chapter_offsets": [1200, 5400, 12000],
  "pages": {
    "1": {
      "end_offset": 2410,
      "input": "that they said nothing",
      "method": "picked"
    },
    "2": {
      "end_offset": 5304,
      "input": "stumping along eastward at a good",
      "method": "picked"
    }
  }
}
```

| Field | Description |
|---|---|
| `title` | Human-readable book title |
| `slug` | URL-safe identifier, also the JSON filename |
| `text_path` | Path to the preprocessed plain-text file |
| `first_page` / `last_page` | Physical page range of the book |
| `current_page` | Next page to map (> `last_page` when complete) |
| `chapters_new_page` | Whether chapter auto-detection was enabled |
| `chapter_offsets` | Character offsets of detected chapter headings in the text |
| `pages` | Map of page number (string key) to boundary data |

Each page entry:

| Field | Description |
|---|---|
| `end_offset` | Character offset in the text where this page **ends** (exclusive) |
| `input` | The search text or chapter heading used to find this boundary |
| `method` | `"picked"` (user selected a word) or `"auto_chapter"` (chapter boundary accepted) |

Page N spans from `pages[N-1].end_offset` (or `0` for the first page) to `pages[N].end_offset`.

</details>

## Exporting Page Text

For custom crib logic beyond the built-in presets, you can export the raw page text. The **Export Pages JSON** button (on the walk-complete screen and Markers page) downloads a `{slug}-pages.json` array:

```json
[
  {"page": 1, "text": "Mr. Utterson the lawyer was a man of a rugged..."},
  {"page": 2, "text": "\"Did you ever remark that door?\" he asked; and..."}
]
```

Also available at `GET /api/<slug>/export`.

## Keyboard Shortcuts

| Key | Context | Action |
|---|---|---|
| `0`-`9` | When candidates are shown | Pick that word as the page boundary |
| `b` / `Backspace` | Walk view (no input focused) | Go back one page |
| `Enter` | Chapter auto-detect prompt | Accept the chapter boundary |
| `Escape` | Search input / edit input | Blur input / close edit panel |

Digit keys work even while the search input is focused — once candidates appear, pressing a digit picks immediately.

## API Reference

All endpoints use the project `slug` as the identifier.

### Project Management

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Home page — list all projects |
| POST | `/project/new` | Create project (multipart form: `title`, `text_file`, `first_page`, `last_page`, `chapters_new_page`) |
| GET | `/project/<slug>` | Walk UI for a project |
| GET | `/project/<slug>/markers` | Markers table UI |
| POST | `/project/<slug>/delete` | Delete a project |

### Walk API (JSON)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/<slug>/state` | Current walk state (progress, page numbers) |
| GET | `/api/<slug>/candidates/<page>?q=...` | Search for boundary candidates. Returns chapter boundary if detected and no `q` param. |
| POST | `/api/<slug>/pick/<page>` | Set page boundary. Body: `{"pos": int, "word": str}` |
| POST | `/api/<slug>/accept_chapter/<page>` | Accept auto-detected chapter boundary |
| POST | `/api/<slug>/goto/<page>` | Jump to page (invalidates pages from that point forward) |

### Markers API (JSON)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/<slug>/markers` | List all mapped page boundaries with snippets |
| POST | `/api/<slug>/edit/<page>` | Re-set a single page boundary in-place. Body: `{"pos": int, "word": str}` |

### Lookup API (JSON)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/<slug>/export` | Export all pages as `[{"page": N, "text": "..."}]` |
| GET | `/api/<slug>/lookup/<page>` | Get full text for a mapped page |
| POST | `/api/<slug>/find` | Find which page contains a phrase. Body: `{"phrase": str}` |

### Crib API (JSON)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/project/<slug>/crib` | Crib builder UI |
| GET | `/api/<slug>/crib/presets` | Available preset rule schemas with knob definitions |
| GET | `/api/<slug>/crib` | Current crib data (rule, knobs, entries) |
| POST | `/api/<slug>/crib/generate` | Generate crib. Body: `{"rule": str, "knobs": {}}` |
| POST | `/api/<slug>/crib/edit/<page>` | Set words for a page. Body: `{"words": [str]}` |
| POST | `/api/<slug>/crib/reset/<page>` | Reset page to rule-generated words |
| GET | `/api/<slug>/crib/export.dat` | Download `.dat` file |
