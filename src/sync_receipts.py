#!/usr/bin/env python3
"""Refresh receipts/ from the public source repositories.

The site is intentionally downstream of the repos: this script copies the
committed receipt files, then src/build.py turns them into the page.
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "receipts"

FILES = {
    "softfp8": "receipts/receipt.json",
    "latq": "receipts/receipt.json",
    "pagemem": "receipts/receipt.json",
    "roofline-planner": "receipts/receipt.json",
    "sdecode": "receipts/receipt.json",
    "fusednorm": "receipts/receipt.json",
    "cplan": "receipts/receipt.json",
    "kvstamp": "receipts/receipt.json",
    "gembench": "receipts/receipt.json",
    "bithash": "receipts/receipt.json",
}

EXTRA = {
    "sdecode-real-run": ("sdecode", "receipts/real_run.json", "sdecode_real_run.json"),
}


def fetch(repo: str, path: str) -> bytes:
    url = f"https://raw.githubusercontent.com/DastanZar/{repo}/main/{path}"
    request = urllib.request.Request(url, headers={"User-Agent": "mlsys-portfolio-build"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def main() -> None:
    DEST.mkdir(exist_ok=True)
    for slug, path in FILES.items():
        data = fetch(slug, path)
        (DEST / f"{slug}.json").write_bytes(data)
        print(f"{slug}: {len(data):,} bytes")

    for label, (repo, path, name) in EXTRA.items():
        data = fetch(repo, path)
        (DEST / name).write_bytes(data)
        print(f"{label}: {len(data):,} bytes")


if __name__ == "__main__":
    main()
