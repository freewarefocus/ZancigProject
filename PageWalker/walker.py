"""
walker.py  -  Core logic for PageWalker

Sequential exact-boundary book mapper. Walks through a book page-by-page,
establishing exact word boundaries via type-to-search + digit-pick.
"""

import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _normalize_for_matching(text: str) -> tuple[str, list[int]]:
    """Strip non-alphanumeric chars, lowercase, collapse whitespace.

    Returns (normalized_text, position_map) where position_map[i] is the
    index in the original text of the i-th character in normalized_text.
    """
    chars = []
    positions = []
    prev_space = False
    for i, ch in enumerate(text):
        if ch.isalnum():
            chars.append(ch.lower())
            positions.append(i)
            prev_space = False
        else:
            if not prev_space and chars:
                chars.append(' ')
                positions.append(i)
                prev_space = True
    if chars and chars[-1] == ' ':
        chars.pop()
        positions.pop()
    return ''.join(chars), positions


def _normalize_phrase(phrase: str) -> str:
    """Normalize a user-entered phrase for matching."""
    chars = []
    prev_space = False
    for ch in phrase:
        if ch.isalnum():
            chars.append(ch.lower())
            prev_space = False
        else:
            if not prev_space and chars:
                chars.append(' ')
                prev_space = True
    if chars and chars[-1] == ' ':
        chars.pop()
    return ''.join(chars)


# ---------------------------------------------------------------------------
# Pre-processing
# ---------------------------------------------------------------------------

def preprocess_gutenberg(raw: str) -> str:
    """Strip Gutenberg boilerplate and collapse chapter-break padding."""
    end_marker = re.search(r'\*{3}\s*END OF.*?\*{3}', raw, re.IGNORECASE)
    if end_marker:
        raw = raw[:end_marker.start()]
    start_marker = re.search(r'\*{3}\s*START OF.*?\*{3}', raw, re.IGNORECASE)
    if start_marker:
        raw = raw[start_marker.end():]

    lines = [l.rstrip() for l in raw.splitlines()]
    result, blank_run = [], 0
    for line in lines:
        if line == '':
            blank_run += 1
        else:
            if blank_run > 0:
                result.append('')
            blank_run = 0
            result.append(line)
    while result and result[-1] == '':
        result.pop()
    return '\n'.join(result)


# ---------------------------------------------------------------------------
# Chapter detection
# ---------------------------------------------------------------------------

CHAPTER_RE = re.compile(
    r'\n((?:CHAPTER|Chapter|chapter)\s+[IVXLCDM\d]+|'
    r'(?:PART|Part)\s+[IVXLCDM\d]+)\b',
)


def detect_chapters(text: str) -> list[int]:
    """Return character offsets of chapter heading lines."""
    return [m.start() for m in CHAPTER_RE.finditer(text)]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class PageData:
    end_offset: int = 0
    input_text: str = ""
    method: str = ""  # "picked" | "auto_chapter"

    def to_dict(self) -> dict:
        return {
            "end_offset": self.end_offset,
            "input": self.input_text,
            "method": self.method,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PageData":
        return cls(
            end_offset=d.get("end_offset", 0),
            input_text=d.get("input", ""),
            method=d.get("method", ""),
        )


@dataclass
class WalkProject:
    title: str
    slug: str
    text_path: str
    first_page: int
    last_page: int
    current_page: int = 1
    chapters_new_page: bool = True
    chapter_offsets: list[int] = field(default_factory=list)
    pages: dict[int, PageData] = field(default_factory=dict)

    # Cached fields (not persisted)
    _text: Optional[str] = field(default=None, repr=False)
    _norm_text: Optional[str] = field(default=None, repr=False)
    _norm_map: Optional[list[int]] = field(default=None, repr=False)

    # ------------------------------------------------------------------
    # Text access
    # ------------------------------------------------------------------

    @property
    def text(self) -> str:
        if self._text is None:
            raw = Path(self.text_path).read_text(encoding='utf-8', errors='replace')
            self._text = preprocess_gutenberg(raw)
        return self._text

    @property
    def norm_text(self) -> str:
        if self._norm_text is None:
            self._norm_text, self._norm_map = _normalize_for_matching(self.text)
        return self._norm_text

    @property
    def norm_map(self) -> list[int]:
        if self._norm_map is None:
            self._norm_text, self._norm_map = _normalize_for_matching(self.text)
        return self._norm_map

    # ------------------------------------------------------------------
    # Page start offset
    # ------------------------------------------------------------------

    def _page_start_offset(self, page: int) -> int:
        """Start offset for a page (= end_offset of previous page, or 0)."""
        if page <= self.first_page:
            return 0
        prev = page - 1
        if prev in self.pages:
            return self.pages[prev].end_offset
        return 0

    # ------------------------------------------------------------------
    # Word boundary helper
    # ------------------------------------------------------------------

    def _find_word_ends_from(self, from_offset: int, to_offset: int,
                             count: int = 10) -> list[dict]:
        """Find consecutive word-end positions starting from the word at from_offset."""
        text = self.text
        # Walk back to start of word containing from_offset
        pos = from_offset
        while pos > 0 and text[pos - 1] not in ' \t\n\r':
            pos -= 1

        word_ends = []
        i = pos
        while i < to_offset and len(word_ends) < count:
            while i < to_offset and text[i] in ' \t\n\r':
                i += 1
            if i >= to_offset:
                break
            word_start = i
            while i < to_offset and text[i] not in ' \t\n\r':
                i += 1
            word_ends.append({"pos": i, "word": text[word_start:i]})

        return word_ends

    # ------------------------------------------------------------------
    # Search candidates (type-to-find within zone)
    # ------------------------------------------------------------------

    def search_candidates(self, page: int, query: str) -> dict:
        """Search for query text within the valid zone for this page.

        Zone: from previous page end to end of text.
        Returns 10 words starting from the first matched word.
        """
        start = self._page_start_offset(page)

        norm_query = _normalize_phrase(query)
        if not norm_query:
            return {"candidates": [], "matched": False}

        # Normalize the zone for searching
        zone_text = self.text[start:]
        norm_zone, pos_map = _normalize_for_matching(zone_text)

        pattern = r"\s+".join(re.escape(w) for w in norm_query.split())
        m = re.search(pattern, norm_zone)
        if not m:
            return {"candidates": [], "matched": False}

        # Map match start back to absolute text offset
        match_start = start + pos_map[m.start()]

        # Get 10 words from match point forward
        word_ends = self._find_word_ends_from(match_start, len(self.text), count=10)

        candidates = [{"index": i, "word": we["word"], "pos": we["pos"]}
                      for i, we in enumerate(word_ends)]

        return {"candidates": candidates, "matched": True}

    # ------------------------------------------------------------------
    # Chapter boundary auto-detection
    # ------------------------------------------------------------------

    def detect_chapter_boundary(self, page: int) -> Optional[dict]:
        """Check if a chapter heading falls within this page's zone.

        Only fires if chapters_new_page is set and we have chapter offsets.
        Looks from previous page end forward through the text for the next
        chapter heading. If found, suggests the boundary just before it.
        """
        if not self.chapters_new_page or not self.chapter_offsets:
            return None

        start = self._page_start_offset(page)

        for ch_offset in self.chapter_offsets:
            if ch_offset <= start:
                continue
            # Found the next chapter heading after our start
            text = self.text

            # Find the last word before the chapter heading
            end_pos = ch_offset
            while end_pos > start and text[end_pos - 1] in ' \t\n\r':
                end_pos -= 1

            if end_pos <= start:
                continue

            # Context: last few words before the heading
            context_start = max(start, end_pos - 80)
            ending_text = text[context_start:end_pos].strip()

            # Chapter heading text
            heading_end = ch_offset + 1
            while heading_end < len(text) and text[heading_end] != '\n':
                heading_end += 1
            heading = text[ch_offset:heading_end].strip()

            return {
                "chapter_offset": ch_offset,
                "end_offset": end_pos,
                "ending_text": ending_text,
                "heading": heading,
            }

        return None

    # ------------------------------------------------------------------
    # Set page boundary
    # ------------------------------------------------------------------

    def set_page_boundary(self, page: int, end_offset: int,
                          method: str, input_text: str = "") -> dict:
        """Record an exact page boundary and advance."""
        self.pages[page] = PageData(
            end_offset=end_offset,
            input_text=input_text,
            method=method,
        )

        if page >= self.current_page:
            self.current_page = page + 1

        return {
            "success": True,
            "page": page,
            "end_offset": end_offset,
            "method": method,
            "next_page": self.current_page,
        }

    # ------------------------------------------------------------------
    # Go back / corrections
    # ------------------------------------------------------------------

    def goto_page(self, page: int) -> dict:
        """Jump to a page, invalidating all pages from page onward."""
        if page < self.first_page:
            page = self.first_page
        if page > self.last_page:
            page = self.last_page

        to_remove = [p for p in self.pages if p >= page]
        count = len(to_remove)

        for p in to_remove:
            del self.pages[p]

        self.current_page = page

        return {
            "success": True,
            "page": page,
            "invalidated": count,
        }

    # ------------------------------------------------------------------
    # Edit a single page boundary in-place (no forward invalidation)
    # ------------------------------------------------------------------

    def edit_page_boundary(self, page: int, end_offset: int,
                           input_text: str = "") -> dict:
        """Re-set a single page's boundary without touching any other pages."""
        if page not in self.pages:
            return {"success": False, "error": f"Page {page} not mapped yet."}

        self.pages[page] = PageData(
            end_offset=end_offset,
            input_text=input_text,
            method="picked",
        )

        return {
            "success": True,
            "page": page,
            "end_offset": end_offset,
        }

    # ------------------------------------------------------------------
    # Query: get mapped page text
    # ------------------------------------------------------------------

    def get_page_text(self, page: int) -> Optional[dict]:
        """Get the exact text for a completed page."""
        if page not in self.pages:
            return None

        start = self._page_start_offset(page)
        end = self.pages[page].end_offset
        text = self.text[start:end].strip()

        return {
            "page": page,
            "text": text,
            "word_count": len(text.split()),
            "char_range": [start, end],
        }

    def get_all_markers(self) -> list[dict]:
        """Return summary of all mapped page boundaries."""
        markers = []
        for pg in sorted(self.pages.keys()):
            pd = self.pages[pg]
            start = self._page_start_offset(pg)
            end = pd.end_offset
            # Last few words of the page
            snippet = self.text[max(start, end - 60):end].strip()
            markers.append({
                "page": pg,
                "end_offset": end,
                "end_words": snippet,
                "method": pd.method,
                "chars": end - start,
            })
        return markers

    # ------------------------------------------------------------------
    # Export: full page text dump
    # ------------------------------------------------------------------

    def export_pages(self) -> list[dict]:
        """Export all mapped pages as a list of {page, text} dicts."""
        out = []
        for pg in sorted(self.pages.keys()):
            start = self._page_start_offset(pg)
            end = self.pages[pg].end_offset
            out.append({"page": pg, "text": self.text[start:end].strip()})
        return out

    # ------------------------------------------------------------------
    # Query: find phrase -> page
    # ------------------------------------------------------------------

    def find_page_for_phrase(self, phrase: str) -> dict:
        """Find which mapped page contains a phrase."""
        phrase = phrase.strip()
        if not phrase:
            return {"error": "Empty phrase."}

        norm_phrase = _normalize_phrase(phrase)
        if not norm_phrase:
            return {"error": "Invalid phrase."}

        pattern = r"\s+".join(re.escape(w) for w in norm_phrase.split())
        m = re.search(pattern, self.norm_text)
        if not m:
            return {"error": f'"{phrase}" not found in text.'}

        orig_start = self.norm_map[m.start()]
        orig_end = self.norm_map[m.end() - 1] + 1
        mid = (orig_start + orig_end) // 2

        for pg in sorted(self.pages.keys()):
            pg_start = self._page_start_offset(pg)
            pg_end = self.pages[pg].end_offset
            if pg_start <= mid < pg_end:
                return {"page": pg, "phrase": phrase, "found": True}

        return {
            "error": "Phrase found in text but not in any mapped page yet.",
            "char_offset": mid,
        }

    # ------------------------------------------------------------------
    # Walk state for UI
    # ------------------------------------------------------------------

    def walk_state(self) -> dict:
        total = self.last_page - self.first_page + 1
        mapped = len(self.pages)
        pct = round(mapped / total * 100) if total > 0 else 0
        done = self.current_page > self.last_page

        return {
            "title": self.title,
            "slug": self.slug,
            "current_page": self.current_page,
            "first_page": self.first_page,
            "last_page": self.last_page,
            "total_pages": total,
            "mapped_pages": mapped,
            "pct_complete": pct,
            "done": done,
            "chapters_new_page": self.chapters_new_page,
            "text_path": self.text_path,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "slug": self.slug,
            "text_path": self.text_path,
            "first_page": self.first_page,
            "last_page": self.last_page,
            "current_page": self.current_page,
            "chapters_new_page": self.chapters_new_page,
            "chapter_offsets": self.chapter_offsets,
            "pages": {str(k): v.to_dict() for k, v in self.pages.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WalkProject":
        proj = cls(
            title=d["title"],
            slug=d["slug"],
            text_path=d["text_path"],
            first_page=d["first_page"],
            last_page=d["last_page"],
            current_page=d.get("current_page", d["first_page"]),
            chapters_new_page=d.get("chapters_new_page", True),
            chapter_offsets=d.get("chapter_offsets", []),
        )
        proj.pages = {
            int(k): PageData.from_dict(v)
            for k, v in d.get("pages", {}).items()
        }
        return proj


# ---------------------------------------------------------------------------
# Project store
# ---------------------------------------------------------------------------

class ProjectStore:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

    def save(self, p: WalkProject):
        (self.data_dir / f"{p.slug}.json").write_text(
            json.dumps(p.to_dict(), indent=2), encoding="utf-8")

    def load(self, slug: str) -> Optional[WalkProject]:
        path = self.data_dir / f"{slug}.json"
        if not path.exists():
            return None
        return WalkProject.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_projects(self) -> list[dict]:
        out = []
        for p in sorted(self.data_dir.glob("*.json")):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                total = d["last_page"] - d["first_page"] + 1
                mapped = len(d.get("pages", {}))
                out.append({
                    "slug": d["slug"],
                    "title": d["title"],
                    "pages": f"{d['first_page']}-{d['last_page']}",
                    "mapped": mapped,
                    "total": total,
                    "pct": round(mapped / total * 100) if total > 0 else 0,
                })
            except Exception:
                pass
        return out

    def delete(self, slug: str) -> bool:
        path = self.data_dir / f"{slug}.json"
        if path.exists():
            path.unlink()
            return True
        return False
