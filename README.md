# Daily Bhagavad Gita Verse

A static site that shows one verse of the Bhagavad Gita each day, with the Sanskrit (Devanagari), a transliteration and an English translation. It's plain HTML, CSS and JavaScript: there's no backend, no build step, and no external API calls at runtime.

- **Verse of the day:** chosen by the date in `America/Los_Angeles`. It stays the same all day, changes at midnight Pacific, and works through all 701 verses in order.
- **Featured mode:** cycles one verse per day through the curated list in `data/featured.json`.
- **Navigation:** Previous / Next / Random / Today buttons (keys: ← → R T).
- **Shareable links:** `index.html#2.47` opens chapter 2, verse 47.
- **Appearance:** light and dark themes follow the system setting, and the layout is mobile-friendly.

## Project layout

```
index.html                 page markup
css/style.css              styles (EB Garamond + Noto Serif Devanagari)
js/app.js                  verse selection, navigation, URL hash handling
data/verses.json           all 701 verses (generated, committed)
data/featured.json         curated verse list, e.g. ["2.47", "18.66"]
scripts/fetch_data.py      one-time script that builds data/verses.json
.github/workflows/deploy.yml   deploys to GitHub Pages on push to main
```

## Setup

1. Push this repository to GitHub, using a `main` branch.
2. In the repo, open **Settings → Pages** and set **Source** to **GitHub Actions**.
3. Push to `main`, or run the workflow by hand from the **Actions** tab. The site is published at `https://<username>.github.io/<repo-name>/`.

All paths are relative, so the site works under any repository subpath.

## Run locally

Browsers block `fetch()` from `file://` pages, so serve the folder over HTTP:

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000/ (or http://localhost:8000/#2.47).

## Editing the featured list

Edit `data/featured.json`. It is a JSON array of `"chapter.verse"` strings. Featured mode cycles through the list in the order given, one verse per day.

## Regenerating the data

`data/verses.json` is already committed, so you only need this if you want to change the data. The script uses only the Python standard library:

```bash
python3 scripts/fetch_data.py
```

It downloads the chapter and verse JSON from [vedicscriptures/bhagavad-gita-data](https://github.com/vedicscriptures/bhagavad-gita-data) and the English text from Wikisource. Then it writes one trimmed file. It warns if any verse is missing a translation.

## Sources and licensing

- **English translation:** Annie Besant, *The Bhagavad-Gita*, 4th edition (1922), via [Wikisource](https://en.wikisource.org/wiki/Bhagavad-Gita_(Besant_4th)). It is public domain: published before 1931 (US), and the translator died in 1933 (life + 70 elsewhere).
- **Sanskrit text, transliteration, chapter names:** [vedicscriptures/bhagavad-gita-data](https://github.com/vedicscriptures/bhagavad-gita-data), GPL-3.0.

**Why not one of the English translations in that repo?** The repo is GPL-3.0, but the translations it bundles are modern works whose copyrights belong to their translators or publishers: Swami Sivananda, Swami Gambirananda, Swami Adidevananda, Dr. S. Sankaranarayan, Shri Purohit Swami (1935, still under US copyright until 2031), and A.C. Bhaktivedanta Swami Prabhupada. The repo's license can't grant reuse rights it doesn't hold, so this site uses a public-domain translation instead.

The Wikisource transcription has small numbering typos (for example, 17.19 and 18.14 are labelled with the next verse's number). The script matches English to Sanskrit using the Devanagari verse number on each Sanskrit block, so these typos don't misalign the text.
