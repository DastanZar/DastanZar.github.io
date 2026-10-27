#!/usr/bin/env python3
"""Export the committed receipts into the standalone app data files.

The apps never retype a number: each `data.js` is generated from the same
`receipts/*.json` snapshots that feed the portfolio page.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECEIPTS = ROOT / "receipts"
APP = ROOT / "app"


def load(name: str) -> dict:
    with (RECEIPTS / f"{name}.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def write(name: str, var: str, data: object) -> None:
    target = APP / name / "data.js"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    target.write_text(f"window.{var} = {payload};\n", encoding="utf-8")
    print(f"{target.relative_to(ROOT)}: {len(payload):,} bytes")


def main() -> None:
    write("sdecode", "SDECODE_DATA", load("sdecode_real_run"))
    write("pagemem", "PAGEMEM_DATA", load("pagemem"))
    write("cplan", "CPLAN_DATA", load("cplan"))
    write("roofline-planner", "ROOFLINE_DATA", load("roofline-planner"))


if __name__ == "__main__":
    main()
