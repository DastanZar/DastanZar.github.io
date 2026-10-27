# DastanZar.github.io

The central portfolio for a series of standalone MLSys / inference systems.
Every number on the page comes from a committed `receipts/*.json` file in one
of the source repositories. The site is a build artifact, not a second copy of
the data.

## What is here

- `index.html`, `styles.css`, `app.js`, `receipts-data.js` — the deployed site.
- `assets/` — the app capture, evidence plates, and paper grain.
- `app/sdecode/` — the live recorded-session demo used by the sdecode case file.
- `app/pagemem/`, `app/cplan/`, `app/roofline-planner/` — the live demos linked from the 20-card inventory.
- `app/kvdesk/` — the KV desk: an interactive tour of attention memory built from the pagemem, kvstamp, and pagedattn receipts.
- `receipts/` — snapshots of each source repo's committed receipt.
- `src/build.py` — extracts values from the receipts, writes the 10 case files and the 20-card inventory.
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
that shows the actual JSON behind the page. The ten case files each get a
receipt-backed artifact; the full 20-repo inventory is a five-theme card grid
with one measured claim per card, plus a one-line plain-language consequence.
A "What didn't work" band publishes the experiments that regressed, because a
receipt you can trust also shows the misses. The application capture is real:
`app/sdecode/session.html`; pagemem, cplan, roofline-planner, and the kv desk
all have runnable demos.
