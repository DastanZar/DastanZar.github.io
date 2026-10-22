# DastanZar.github.io

The central portfolio for a series of standalone MLSys / inference systems.
Every number on the page comes from a committed `receipts/*.json` file in one
of the source repositories. The site is a build artifact, not a second copy of
the data.

## What is here

- `index.html`, `styles.css`, `app.js`, `receipts-data.js` — the deployed site.
- `assets/` — the app capture, evidence plates, and paper grain.
- `app/sdecode/` — the live recorded-session demo used by the sdecode case file.
- `receipts/` — snapshots of each source repo's committed receipt.
- `src/build.py` — extracts values from the receipts and writes the page.
- `src/sync_receipts.py` — refreshes the receipts from the public repos.

## Build

```bash
python src/sync_receipts.py   # optional: pull latest committed receipts
python src/build.py
```

`build.py` asserts the headline claims against the receipts, so a drifting
number fails the build instead of quietly changing the page.

Open `index.html` directly, or serve the directory:

```bash
python -m http.server 8000
```

Use `index.html?static=1` to render with entrance motion disabled (useful for
screenshots and visual tests).

## Design notes

Warm paper, ink typography, one signal colour, and a receipt-console section
that shows the actual JSON behind the page. The three featured systems each
get an evidence plate; the remaining seven are an index with a hover receipt
card. The application capture is real: `app/sdecode/session.html`.
