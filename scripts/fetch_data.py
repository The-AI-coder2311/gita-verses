#!/usr/bin/env python3
"""Build data/verses.json (run once; the output is committed).

Sanskrit, transliteration and chapter names come from
github.com/vedicscriptures/bhagavad-gita-data (GPL-3.0).

The English is Annie Besant's public-domain translation (4th ed., 1922),
taken from the Wikisource transcription. The translations bundled in the
vedicscriptures repo are modern copyrighted works the repo license cannot
grant reuse rights for, so none of them is used.

Usage: python3 scripts/fetch_data.py   (stdlib only)
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path

VS_BASE = "https://raw.githubusercontent.com/vedicscriptures/bhagavad-gita-data/main"
WS_PAGE = "https://en.wikisource.org/w/index.php?title={}&action=render"
WS_TITLE = "Bhagavad-Gita_(Besant_4th)/Discourse_{}"
TRANSLATOR = "Annie Besant"
SOURCE = "The Bhagavad-Gita, translated by Annie Besant, 4th edition (1922), public domain"
SOURCE_URL = "https://en.wikisource.org/wiki/Bhagavad-Gita_(Besant_4th)"
USER_AGENT = "gita-verses-data-script/1.0 (one-time static site data build)"
OUT = Path(__file__).resolve().parent.parent / "data" / "verses.json"


def get(url, retries=5):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8")
        except Exception as e:
            if attempt == retries - 1:
                raise
            wait = 5 * 2**attempt
            print(f"  retry {url} in {wait}s ({e})", file=sys.stderr)
            time.sleep(wait)


def get_json(url):
    return json.loads(get(url))


DEVANAGARI_DIGITS = "०१२३४५६७८९"


def clean_sanskrit(text):
    text = re.sub(r"\|\|[^|]*\|\|\s*$", "", text.strip())  # trailing ||२-४७||
    text = text.replace("||", "॥").replace("|", "।")
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    return "\n".join(lines)


def clean_translit(text):
    text = re.sub(r"\|\|[^|]*\|\|\s*$", "", text.strip())
    lines = []
    for ln in text.split("\n"):
        ln = re.sub(r"\s*\.\s*$", "", ln.strip())  # trailing "." stands in for a danda
        ln = re.sub(r"(?<=\w)\.(?=\w)", "'", ln)  # internal "." stands in for an avagraha
        if ln:
            lines.append(ln)
    return "\n".join(lines)


VOID_TAGS = {"br", "link", "meta", "img", "hr", "wbr"}


class BesantParser(HTMLParser):
    """Splits a Wikisource discourse page into ("sa", text) / ("en", text) blocks."""

    def __init__(self):
        super().__init__()
        self.depth = 0
        self.sa_depth = None  # depth of the enclosing lang="sa" block
        self.skip_depth = None  # inside <sup> footnote markers, <style>, references
        self.p_depth = None
        self.buf = []
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            if tag == "br":
                self.buf.append(" ")  # survives whitespace collapsing as a line break
            return
        self.depth += 1
        a = dict(attrs)
        if self.skip_depth is None and (
            tag in ("sup", "style", "script") or "references" in (a.get("class") or "")
        ):
            self.skip_depth = self.depth
        if self.sa_depth is None and a.get("lang") == "sa":
            self.sa_depth = self.depth
            self.buf = []
        elif tag == "p" and self.sa_depth is None and self.p_depth is None:
            self.p_depth = self.depth
            self.buf = []

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if tag == "p" and self.sa_depth is not None:
            self.buf.append("\n")
        if self.skip_depth == self.depth:
            self.skip_depth = None
        if self.sa_depth == self.depth:
            self.sa_depth = None
            self.blocks.append(("sa", "".join(self.buf)))
        if self.p_depth == self.depth:
            self.p_depth = None
            text = re.sub(r"[^\S ]+", " ", "".join(self.buf).replace("​", ""))
            text = re.sub(r" *  *", "\n", text).strip()
            if text:
                self.blocks.append(("en", text))
        self.depth -= 1

    def handle_data(self, data):
        if self.skip_depth is None and (self.sa_depth is not None or self.p_depth is not None):
            self.buf.append(data)


def deva_int(s):
    return int("".join(str(DEVANAGARI_DIGITS.index(ch)) if ch in DEVANAGARI_DIGITS else ch for ch in s))


VERSE_NUM_RE = re.compile(r"\s*\(?\s*(\d+)\s*\)?\s*$")


def fetch_besant(chapter):
    """Returns {verse_number: english_text}, keyed by the Devanagari number on each Sanskrit block."""
    title = urllib.parse.quote(WS_TITLE.format(chapter), safe="_()/-")
    p = BesantParser()
    p.feed(get(WS_PAGE.format(title)))

    verses = {}
    current, parts, closed = None, [], False

    def flush():
        if current is not None and parts:
            verses[current] = " ".join(parts)

    for kind, text in p.blocks:
        if kind == "sa":
            m = re.search(r"॥\s*([०-९]+)\s*॥\s*$", text.strip())
            if not m:
                continue  # headings such as the opening invocation
            flush()
            current, parts, closed = deva_int(m.group(1)), [], False
        elif current is not None and not closed:
            if text.startswith("Thus, in the") or text.startswith("Thus in the"):
                closed = True  # chapter colophon
                continue
            m = VERSE_NUM_RE.search(text)
            if m and (text.endswith(")") or text.rstrip()[-1].isdigit()):
                n = int(m.group(1))
                if n != current:
                    print(f"  note {chapter}.{current}: English labelled ({n}); using Sanskrit number", file=sys.stderr)
                text = text[: m.start()]
                closed = True
            parts.append(text.strip())
    flush()
    return verses


def tidy_english(text):
    text = re.sub(r" +([,;:.!?])", r"\1", text)
    return re.sub(r"\n+", "\n", text).strip()


def main():
    print("Fetching chapters…")
    chapters = {}
    for c in range(1, 19):
        d = get_json(f"{VS_BASE}/chapter/bhagavadgita_chapter_{c}.json")
        chapters[c] = {
            "count": int(d["verses_count"]),
            "name": d["translation"].strip(),
            "name_sa": d["name"].strip(),
            "meaning": (d.get("meaning") or {}).get("en", "").strip(),
        }

    keys = [(c, v) for c in range(1, 19) for v in range(1, chapters[c]["count"] + 1)]
    print(f"Fetching {len(keys)} verses…")

    def fetch_slok(key):
        c, v = key
        return key, get_json(f"{VS_BASE}/slok/bhagavadgita_chapter_{c}_slok_{v}.json")

    with ThreadPoolExecutor(max_workers=8) as pool:
        sloks = dict(pool.map(fetch_slok, keys))

    print("Fetching Besant translation from Wikisource…")
    english = {}
    for c in range(1, 19):
        english[c] = fetch_besant(c)
        print(f"  chapter {c}: {len(english[c])} verses")
        time.sleep(2)

    verses, missing = [], []
    for c, v in keys:
        s = sloks[(c, v)]
        en = english[c].get(v)
        if not en:
            missing.append(f"{c}.{v}")
        entry = {
            "chapter": c,
            "verse": v,
            "chapter_name": chapters[c]["name"],
            "chapter_name_sa": chapters[c]["name_sa"],
            "chapter_meaning": chapters[c]["meaning"],
            "sanskrit": clean_sanskrit(s["slok"]),
            "transliteration": clean_translit(s["transliteration"]),
            "translation": tidy_english(en) if en else "",
            "translator": TRANSLATOR,
        }
        verses.append(entry)

    extra = [f"{c}.{v}" for c in english for v in english[c] if v > chapters[c]["count"]]
    if missing or extra:
        print(f"WARNING missing English: {missing}\nWARNING unmatched English: {extra}", file=sys.stderr)

    out = {
        "translator": TRANSLATOR,
        "source": SOURCE,
        "source_url": SOURCE_URL,
        "sanskrit_source": "github.com/vedicscriptures/bhagavad-gita-data (GPL-3.0)",
        "verses": verses,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {len(verses)} verses to {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
