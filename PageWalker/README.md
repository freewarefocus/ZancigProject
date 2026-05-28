# PageWalker

Sequential exact-boundary book mapper. Maps plain-text books to physical page numbers so you can build page-level cribs for book tests.

## The Book Test Use Case

A **book test** is a mentalism effect where a spectator opens a book to any page and the performer reveals what's written there. To perform this, you need a **crib** — a cheat sheet mapping page numbers to memorable words or phrases from that page.

The problem: you need the *exact* text on each physical page, but all you have is a continuous digital text file (e.g., from Project Gutenberg). Page breaks in the printed edition don't exist in the `.txt` file.

PageWalker solves this by letting you walk through the book page-by-page with the physical copy in hand, marking exactly where each page ends in the digital text. The output is a JSON file that maps every page number to its precise character range, which you can then use to extract text for crib building.

This works especially well with cheap **Dover Thrift Editions** and other public-domain printings where the text is freely available on Gutenberg.

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

## JSON Output Format

Completed walks are saved to `data/{slug}.json`. Here's the schema:

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

### Field Reference

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

### Page Boundary Data

| Field | Description |
|---|---|
| `end_offset` | Character offset in the text where this page **ends** (exclusive) |
| `input` | The search text or chapter heading used to find this boundary |
| `method` | `"picked"` (user selected a word) or `"auto_chapter"` (chapter boundary accepted) |

### Start/End Offset Logic

Each page's text spans from the *previous* page's `end_offset` to this page's `end_offset`:

- **Page N start** = `pages[N-1].end_offset` (or `0` for the first page)
- **Page N end** = `pages[N].end_offset`

## Exporting Page Text

The easiest way to get page text out is the **Export Pages JSON** button, available on both the walk-complete screen and the Markers page. It downloads a `{slug}-pages.json` file — a flat JSON array where each entry is one page:

```json
[
  {"page": 1, "text": "Mr. Utterson the lawyer was a man of a rugged..."},
  {"page": 2, "text": "\"Did you ever remark that door?\" he asked; and..."},
  {"page": 3, "text": "From that time forward, Mr. Utterson began to..."}
]
```

JSON handles all the escaping (quotes, unicode, etc.) so this never breaks regardless of what's in the text. You can also hit the endpoint directly: `GET /api/<slug>/export`.

From there, building a crib is trivial:

```python
import json
pages = json.loads(open("the-strange-case-of-dr-jekyll-and-mr-hyde-pages.json").read())
for p in pages:
    first_line = p["text"].split('\n')[0]
    print(f"Page {p['page']}: {first_line}")
```

## Using the Raw Project JSON

For more control, you can work with the raw project file (`data/{slug}.json`) and the source text directly:

```python
import json
from pathlib import Path

data = json.loads(Path("data/the-strange-case-of-dr-jekyll-and-mr-hyde.json").read_text())
text = Path(data["text_path"]).read_text(encoding="utf-8")

# Strip Gutenberg boilerplate the same way PageWalker does:
import re
end = re.search(r'\*{3}\s*END OF.*?\*{3}', text, re.IGNORECASE)
if end: text = text[:end.start()]
start = re.search(r'\*{3}\s*START OF.*?\*{3}', text, re.IGNORECASE)
if start: text = text[start.end():]

def get_page(page_num):
    pages = data["pages"]
    prev = str(page_num - 1)
    curr = str(page_num)
    if curr not in pages:
        return None
    start = pages[prev]["end_offset"] if prev in pages else 0
    end = pages[curr]["end_offset"]
    return text[start:end].strip()

# First line of page 12 — a typical crib entry
page_text = get_page(12)
if page_text:
    first_line = page_text.split('\n')[0]
    print(f"Page 12: {first_line}")
```

From there, you can build whatever crib format you need — first words, last words, key phrases, full page dumps, etc.

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
