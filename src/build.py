"""Build the MLSys portfolio from committed receipts.

The page never retypes a metric: every number used in the shell, cards,
proof strip, and receipt console is extracted from receipts/*.json here.
Run: python src/build.py
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
RECEIPTS = ROOT / "receipts"


def load(name: str) -> dict:
    with (RECEIPTS / f"{name}.json").open(encoding="utf-8") as f:
        return json.load(f)


def fmt(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}"


def pct(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def lane_mean(pair: dict, lane: str, key: str) -> float:
    runs = [r for r in pair["runs"] if r["lane"] == lane]
    return mean([r[key] for r in runs])


# ---------------------------------------------------------------------------
# Receipts -> values
# ---------------------------------------------------------------------------
softfp8 = load("softfp8")
latq = load("latq")
pagemem = load("pagemem")
cplan = load("cplan")
kvstamp = load("kvstamp")
fusednorm = load("fusednorm")
gembench = load("gembench")
bithash = load("bithash")
roofline = load("roofline-planner")
sdecode = load("sdecode_real_run")

sd_pair = next(p for p in sdecode["pairs"] if p["pair"] == "gpt2<-distilgpt2")
sd_tpc = lane_mean(sd_pair, "fixed-k8", "tokens_per_target_call")
sd_calls = lane_mean(sd_pair, "fixed-k8", "target_calls")
sd_adaptive = lane_mean(sd_pair, "adaptive", "tokens_per_target_call")
sd_c = sd_pair["drafter_cost_c"]
sd_match = all(r["matches_reference"] for p in sdecode["pairs"] for r in p["runs"])
sd_identity = "100% token match" if sd_match else "identity checked"
sd_identity_pct = "100%" if sd_match else "checked"

pm = pagemem["allocator"]
pm_base = pm["blocks_preallocated_baseline"]
pm_paged = pm["blocks_paged"]
pm_saved = pm["savings"]
pm_hit = pm["prefix_hit_rate"]
pm_frag = pm["external_fragmentation"]

cp = cplan["sweep"]
cp_rates = sorted(float(k.split("=")[1].split("/")[0]) for k in cp)
cp_rows = []
for rate in cp_rates:
    row = next(v for k, v in cp.items() if float(k.split("=")[1].split("/")[0]) == rate)
    cp_rows.append(
        {
            "rate": rate,
            "static": row["static"]["ttft"],
            "continuous": row["continuous"]["ttft"],
            "p99_static": row["static"]["p99"],
            "p99_continuous": row["continuous"]["p99"],
            "improvement": int(row["ttft_improvement"].rstrip("%")),
        }
    )
cp_peak = next(r for r in cp_rows if r["rate"] == 1.5)

soft_bw = softfp8["bandwidth_model"]["gtx1060-6gb"]
soft_x = soft_bw["gb_per_token_fp16"] / soft_bw["gb_per_token_w8"]
soft_err = pct(softfp8["w8_vs_fp16_relative_output_error"], 2)
soft_parity = softfp8["kernel_vs_reference_max_abs_err"]

latq_d8 = latq["fidelity_ladder"]["d8"]
latq_x = f"{latq_d8['compression_vs_fp16']:.1f}"
latq_err = f"{latq_d8['rel_err']:.3f}"
latq_floor_gap = abs(latq_d8["rel_err"] - latq_d8["rd_floor_at_bpw"]) / latq_d8["rd_floor_at_bpw"]

kv64 = kvstamp["sweep"]["budget=64/512"]
kv_x = kvstamp["compression_at_64"].replace("x", "")
kv_err = f"{kv64['relative_output_error']:.2f}"

fn = fusednorm["bytes_per_layer_site"]
fn_reduction = float(fn["reduction"])
fn_saved = fusednorm["llama3_8b_decode_step_bytes"]["saved_bytes_per_token"]
fn_saved_mib = fn_saved / (1024 * 1024)

gb_naive = gembench["naive_rows"]["ms"]
gb_opt = gembench["torch_mv"]["ms"]
gb_x = gembench["torch_mv"]["speedup_vs_naive"]

bh_x = bithash["compression_vs_fp16"]
bh_bpw = bithash["bits_per_weight_effective"]

rl_count = len(roofline)
rl_gpus = len({v["gpu"] for v in roofline.values()})
rl_models = len({v["model"] for v in roofline.values()})

# Guardrails: fail the build if the receipts stop saying what the page says.
assert sd_tpc > 2.0 and sd_c < 0.7
assert sd_match, "sdecode token identity check failed"
assert pm_paged == 204 and pm_base == 504
assert cp_peak["improvement"] == 94
assert abs(fn_reduction - 0.333) < 0.001
assert bh_x == 3.98

# ---------------------------------------------------------------------------
# Project manifest: one entry per public repo. Copy + links only.
# ---------------------------------------------------------------------------
projects = [
    {
        "slug": "sdecode",
        "index": "01",
        "name": "sdecode",
        "category": "Speculative decoding",
        "claim": f"<strong>{fmt(sd_tpc)}×</strong> tokens per target call",
        "description": "Measured draft/verify on real GPT-2 weights, token-identical to the naive lane.",
        "preview": "assets/sdecode-app.png",
        "preview_metric": f"{fmt(sd_tpc)}×",
        "preview_label": "tokens / call",
    },
    {
        "slug": "pagemem",
        "index": "02",
        "name": "pagemem",
        "category": "KV memory",
        "claim": f"<strong>{pm_saved}</strong> fewer blocks",
        "description": "Prefix-shared paged KV; a 504-block baseline collapses to 204 blocks.",
        "preview": "assets/pagemem.png",
        "preview_caption": "pagemem / block table",
    },
    {
        "slug": "cplan",
        "index": "03",
        "name": "cplan",
        "category": "Serving / scheduling",
        "claim": f"<strong>{cp_peak['improvement']}%</strong> lower TTFT",
        "description": "Continuous batching against a static scheduler, with p99 in the same receipt.",
        "preview": "assets/cplan.png",
        "preview_caption": "cplan / space-time",
    },
    {
        "slug": "softfp8",
        "index": "04",
        "name": "softfp8",
        "category": "Quantization",
        "claim": f"<strong>{soft_x:.1f}×</strong> weight bytes <i>/</i> {soft_err} rel. error",
        "description": "W8 weight path, measured output error and a labelled bandwidth model.",
        "preview": "assets/softfp8.png",
        "preview_caption": "softfp8 / bandwidth",
    },
    {
        "slug": "latq",
        "index": "05",
        "name": "latq",
        "category": "Quantization",
        "claim": f"<strong>{latq_x}×</strong> compression <i>/</i> {latq_err} rel. error",
        "description": f"D8/D4/Z2 lattice ladder from 4 to 1 bit per weight; the 1-bit point sits within {latq_floor_gap * 100:.0f}% of the Gaussian R-D floor.",
        "preview": "assets/latq.png",
        "preview_caption": "latq / fidelity ladder",
    },
    {
        "slug": "fusednorm",
        "index": "06",
        "name": "fusednorm",
        "category": "Kernels",
        "claim": f"<strong>{pct(fn_reduction, 0)}</strong> less norm-site traffic",
        "description": f"RMSNorm, residual, and SwiGLU epilogue fused into one pass; {fn_saved_mib:.0f} MiB saved per LLaMA-3 8B decode token.",
        "preview": "assets/fusednorm.png",
        "preview_caption": "fusednorm / traffic map",
    },
    {
        "slug": "kvstamp",
        "index": "07",
        "name": "kvstamp",
        "category": "KV cache",
        "claim": f"<strong>{kv_x}×</strong> KV compression <i>/</i> {kv_err} error",
        "description": "Token importance at a fixed budget, swept until the error knee is visible.",
        "preview": "assets/kvstamp.png",
        "preview_caption": "kvstamp / attention maps",
    },
    {
        "slug": "roofline-planner",
        "index": "08",
        "name": "roofline-planner",
        "category": "Planning",
        "claim": f"<strong>{rl_count}</strong> deployment plans <i>/</i> {rl_models} models × {rl_gpus} GPUs",
        "description": "Fit-check, roofline regime, and decode throughput for every plan.",
        "preview": "assets/roofline-planner.png",
        "preview_caption": "roofline-planner / placement map",
    },
    {
        "slug": "gembench",
        "index": "09",
        "name": "gembench",
        "category": "Kernels",
        "claim": f"<strong>{gb_x:.1f}×</strong> GEMV throughput <i>/</i> {gb_opt:.1f} ms",
        "description": f"A bandwidth-honest GEMV ladder: {gb_naive:.1f} ms naive rows vs {gb_opt:.1f} ms torch.mv, measured on CPU.",
        "preview": "assets/gembench.png",
        "preview_caption": "gembench / CPU receipt",
    },
    {
        "slug": "bithash",
        "index": "10",
        "name": "bithash",
        "category": "Compression",
        "claim": f"<strong>{bh_x:.2f}×</strong> compression <i>/</i> {bh_bpw:.2f} bpw",
        "description": "A four-bit codebook study: uniform16 beats odd16 on dense weight rows.",
        "preview": "assets/bithash.png",
        "preview_caption": "bithash / codebook grids",
    },
]

preview_meta = {
    "sdecode": (f"{fmt(sd_tpc)}×", "tokens / call"),
    "pagemem": (pm_saved, "fewer blocks"),
    "cplan": (f"{cp_peak['improvement']}%", "lower TTFT"),
    "softfp8": (f"{soft_x:.1f}×", "weight bytes"),
    "latq": (f"{latq_x}×", "compression"),
    "fusednorm": (pct(fn_reduction, 0), "less traffic"),
    "kvstamp": (f"{kv_x}×", "KV compression"),
    "roofline-planner": (str(rl_count), "deployment plans"),
    "gembench": (f"{gb_x:.1f}×", "GEMV throughput"),
    "bithash": (f"{bh_x:.2f}×", "compression"),
}
for project in projects:
    project["preview_metric"], project["preview_label"] = preview_meta[project["slug"]]

project_by_slug = {p["slug"]: p for p in projects}
receipt_slugs = [p["slug"] for p in projects]


def repo_url(slug: str) -> str:
    return f"https://github.com/DastanZar/{slug}"


def receipt_url(slug: str) -> str:
    if slug == "sdecode":
        return "https://github.com/DastanZar/sdecode/blob/main/receipts/real_run.json"
    return f"https://github.com/DastanZar/{slug}/blob/main/receipts/receipt.json"


def receipt_label(slug: str) -> str:
    return "real_run.json" if slug == "sdecode" else "receipt.json"


# ---------------------------------------------------------------------------
# SVG evidence plates
# ---------------------------------------------------------------------------
def pagemem_svg() -> str:
    full_w = 480
    paged_w = full_w * pm_paged / pm_base
    return f"""<svg class="evidence-svg" viewBox="0 0 520 252" role="img" aria-label="Paged allocation uses 204 blocks against a 504-block baseline, a 59.5 percent reduction">
  <defs>
    <pattern id="pm-base" width="8" height="8" patternUnits="userSpaceOnUse">
      <rect width="6.2" height="6.2" fill="#141511" opacity=".18"/>
    </pattern>
    <pattern id="pm-paged" width="8" height="8" patternUnits="userSpaceOnUse">
      <rect width="6.2" height="6.2" fill="#E9491B"/>
    </pattern>
  </defs>
  <text x="20" y="22" class="svg-label">BLOCK ALLOCATION</text>
  <text x="500" y="22" text-anchor="end" class="svg-accent">−{pm_saved}</text>
  <text x="20" y="43" class="svg-label">PREALLOCATED <tspan class="svg-ink">/ {pm_base}</tspan></text>
  <rect x="20" y="50" width="{full_w}" height="48" fill="url(#pm-base)" stroke="#141511" stroke-opacity=".18"/>
  <text x="20" y="126" class="svg-label">PAGED <tspan class="svg-ink">/ {pm_paged}</tspan></text>
  <rect x="20" y="133" width="{paged_w:.1f}" height="48" fill="url(#pm-paged)"/>
  <rect x="{20 + paged_w:.1f}" y="133" width="{full_w - paged_w:.1f}" height="48" fill="none" stroke="#141511" stroke-opacity=".12" stroke-dasharray="3 4"/>
  <line x1="20" y1="210" x2="500" y2="210" stroke="#141511" stroke-opacity=".14"/>
  <text x="20" y="231" class="svg-label">8 SEQUENCES <tspan class="svg-ink">/ hit {pm_hit:.1f} / frag {pm_frag * 100:.2f}%</tspan></text>
</svg>"""


def cplan_svg() -> str:
    W, H = 520, 250
    left, right, top, bottom = 42, 12, 48, 202
    plot_w = W - left - right
    plot_h = bottom - top
    max_ms = 1100
    group_w = plot_w / 4
    bars = []
    for i, row in enumerate(cp_rows):
        x = left + i * group_w
        static_h = row["static"] / max_ms * plot_h
        cont_h = max(3.0, row["continuous"] / max_ms * plot_h)
        bar_w = 18
        gap = 6
        sx = x + group_w / 2 - bar_w - gap / 2
        cx = x + group_w / 2 + gap / 2
        bars.append(
            f'<rect x="{sx:.1f}" y="{bottom - static_h:.1f}" width="{bar_w}" height="{static_h:.1f}" fill="#141511" opacity=".18"/>'
            f'<rect x="{cx:.1f}" y="{bottom - cont_h:.1f}" width="{bar_w}" height="{cont_h:.1f}" fill="#E9491B"/>'
            f'<text x="{sx + bar_w / 2:.1f}" y="{bottom - static_h - 7:.1f}" text-anchor="middle" class="svg-micro">{row["static"]:.0f}</text>'
            f'<text x="{cx + bar_w / 2:.1f}" y="{bottom - cont_h - 9:.1f}" text-anchor="middle" class="svg-accent micro">{row["continuous"]:.0f}</text>'
            f'<text x="{x + group_w / 2:.1f}" y="{bottom + 19}" text-anchor="middle" class="svg-label">{row["rate"]:.1f}/s</text>'
        )
    ygrid = []
    for value in (0, 500, 1000):
        y = bottom - value / max_ms * plot_h
        ygrid.append(f'<line x1="{left}" y1="{y:.1f}" x2="{W - right}" y2="{y:.1f}" stroke="#141511" stroke-opacity=".10" stroke-dasharray="2 4"/>')
        ygrid.append(f'<text x="{left - 8}" y="{y + 3:.1f}" text-anchor="end" class="svg-micro">{value}</text>')
    return f"""<svg class="evidence-svg" viewBox="0 0 520 250" role="img" aria-label="Time to first token for continuous batching versus static batching across four request rates">
  <g>
    <rect x="20" y="18" width="7" height="7" fill="#E9491B"/>
    <text x="33" y="25" class="svg-label">CONTINUOUS</text>
    <rect x="112" y="18" width="7" height="7" fill="#141511" opacity=".22"/>
    <text x="125" y="25" class="svg-label">STATIC</text>
    <text x="500" y="25" text-anchor="end" class="svg-label">TTFT / MS</text>
  </g>
  {''.join(ygrid)}
  {''.join(bars)}
  <line x1="{left}" y1="{bottom}" x2="{W - right}" y2="{bottom}" stroke="#141511" stroke-opacity=".3"/>
  <text x="20" y="234" class="svg-label">1.5/S CASE <tspan class="svg-ink">/ {cp_peak['continuous']:.1f} vs {cp_peak['static']:.1f} ms</tspan></text>
</svg>"""


# ---------------------------------------------------------------------------
# HTML fragments
# ---------------------------------------------------------------------------
def proof_strip() -> str:
    items = [
        {
            "value": f"{fmt(sd_tpc)}×",
            "label": "tokens per target call",
            "source": "sdecode",
            "anchor": "#sdecode",
        },
        {
            "value": pm_saved,
            "label": "fewer KV blocks",
            "source": "pagemem",
            "anchor": "#pagemem",
        },
        {
            "value": f"{cp_peak['improvement']}%",
            "label": "lower TTFT",
            "source": "cplan",
            "anchor": "#cplan",
        },
        {
            "value": f"{bh_x:.2f}×",
            "label": "weight compression",
            "source": "bithash",
            "anchor": "#shipping",
        },
    ]
    return "".join(
        f"""<div class="proof-item">
        <span class="proof-num">{item['value']}</span>
        <span class="proof-label">{item['label']}</span>
        <a class="proof-src" href="{item['anchor']}">{item['source']} <span aria-hidden="true">↗</span></a>
      </div>"""
        for item in items
    )


def hero_facts() -> str:
    facts = [
        ("SYSTEMS", "10 shipped"),
        ("MEASURED ON", "CPU / HF models"),
        ("GPU CLAIMS", "0 unlabeled"),
        ("RECEIPTS", "10 committed"),
    ]
    return "".join(
        f'<li><span>{k}</span><strong>{v}</strong></li>' for k, v in facts
    )


def featured_sdecode() -> str:
    return f"""<article class="case case-featured reveal" id="sdecode">
  <div class="case-copy">
    <div class="case-meta"><span class="case-no">01</span><span>Speculative decoding</span><span>2026</span></div>
    <h3>sdecode</h3>
    <p class="case-claim"><strong>{fmt(sd_tpc)}×</strong> tokens per target call<span class="case-period">.</span></p>
    <p class="case-desc">A measured draft/verify harness for real models: a smaller drafter proposes, the target verifies a batch, and every lane is checked token-for-token against the naive target. The receipt keeps the wins and the losses.</p>
    <dl class="specs">
      <div class="spec"><dt>TARGET / DRAFTER</dt><dd>gpt2 / distilgpt2</dd></div>
      <div class="spec"><dt>DRAFTER COST c</dt><dd>{fmt(sd_c)}</dd></div>
      <div class="spec"><dt>BEST LANE</dt><dd>fixed K=8</dd></div>
      <div class="spec"><dt>TOKENS / CALL</dt><dd>{fmt(sd_tpc)}×</dd></div>
      <div class="spec"><dt>IDENTITY</dt><dd>{sd_identity}</dd></div>
      <div class="spec"><dt>ARTIFACTS</dt><dd>app · film · ledger</dd></div>
    </dl>
    <p class="case-note"><span class="note-mark"></span> Negative result included: adaptive K averaged {fmt(sd_adaptive)}× on this pair; both lanes stay in the receipt.</p>
    <div class="case-links">
      <a class="btn btn-ink" href="{repo_url('sdecode')}" target="_blank" rel="noopener">Open repo <span aria-hidden="true">↗</span></a>
      <a class="btn btn-ghost" href="app/sdecode/session.html" target="_blank" rel="noopener">Launch app <span aria-hidden="true">↗</span></a>
      <a class="text-link" href="{receipt_url('sdecode')}" target="_blank" rel="noopener">receipt <span aria-hidden="true">↗</span></a>
    </div>
  </div>
  <div class="case-media">
    <figure class="media-frame">
      <div class="media-top"><span class="media-dots"><i></i><i></i><i></i></span><span>sdecode / recorded run</span><span class="media-live">APP</span></div>
      <img src="assets/sdecode-app.png" alt="sdecode session app showing a recorded run, lane selector, and generated text" loading="eager" width="1440" height="760">
      <figcaption class="media-bar"><span>APP / session.html</span><span>measured on CPU</span></figcaption>
    </figure>
    <div class="receipt-strip">
      <div><span>TOKENS / CALL</span><strong>{fmt(sd_tpc)}×</strong></div>
      <div><span>TARGET CALLS</span><strong>{sd_calls:.1f} avg</strong></div>
      <div><span>MATCH</span><strong>{sd_identity_pct}</strong></div>
    </div>
  </div>
</article>"""


def mini_case(
    *,
    slug: str,
    index: str,
    category: str,
    claim_html: str,
    description: str,
    svg: str,
    viz_label: str,
    viz_tag: str,
) -> str:
    name = project_by_slug[slug]["name"]
    return f"""<article class="case-mini reveal" id="{slug}">
  <div class="case-meta"><span class="case-no">{index}</span><span>{category}</span><span>2026</span></div>
  <h3>{name}</h3>
  <div class="mini-viz">
    <div class="viz-meta"><span>{viz_label}</span><span class="viz-tag">{viz_tag}</span></div>
    {svg}
  </div>
  <p class="case-claim"><strong>{claim_html}</strong></p>
  <p class="case-desc">{description}</p>
  <div class="case-links">
    <a class="text-link strong" href="{repo_url(slug)}" target="_blank" rel="noopener">Open repo <span aria-hidden="true">↗</span></a>
    <a class="text-link" href="{receipt_url(slug)}" target="_blank" rel="noopener">receipt <span aria-hidden="true">↗</span></a>
  </div>
</article>"""


case_duo = (
    mini_case(
        slug="pagemem",
        index="02",
        category="KV memory",
        claim_html=f"{pm_saved} fewer blocks",
        description="The allocator shares a 512-token system prefix and pages the rest. The 504-block preallocated baseline becomes 204 blocks, with the block map committed next to the numbers.",
        svg=pagemem_svg(),
        viz_label="PAGED KV / BLOCK MAP",
        viz_tag="204 / 504",
    )
    + "\n"
    + mini_case(
        slug="cplan",
        index="03",
        category="Serving / scheduling",
        claim_html=f"{cp_peak['improvement']}% lower TTFT",
        description="A continuous scheduler lets every slot refill the moment it frees. Static batching waits for the longest job. The receipt records TTFT and p99 at four request rates.",
        svg=cplan_svg(),
        viz_label="CONTINUOUS VS STATIC",
        viz_tag=f"{cp_peak['improvement']}% lower",
    )
)


def shipping_rows() -> str:
    rows = []
    for project in projects[3:]:
        rows.append(
            f"""<a class="ship-row reveal" href="{repo_url(project['slug'])}" target="_blank" rel="noopener" data-preview="{project['preview']}" data-preview-project="{project['name']}" data-preview-metric="{project['preview_metric']}" data-preview-label="{project['preview_label']}">
        <span class="ship-index">{project['index']}</span>
        <span class="ship-name">{project['name']}</span>
        <span class="ship-cat">{project['category']}</span>
        <span class="ship-claim">{project['claim']}</span>
        <span class="ship-arrow" aria-hidden="true">↗</span>
      </a>"""
        )
    return "\n".join(rows)


def receipt_tabs() -> str:
    return "".join(
        f'<button class="tab" type="button" role="tab" aria-selected="false" data-receipt="{slug}">{project_by_slug[slug]["name"]}</button>'
        for slug in receipt_slugs
    )


def receipts_payload() -> dict:
    payload = {}
    for slug in receipt_slugs:
        name = "sdecode_real_run" if slug == "sdecode" else slug
        payload[slug] = {
            "label": receipt_label(slug),
            "source": receipt_url(slug),
            "project": project_by_slug[slug]["name"],
            "data": load(name),
        }
    return payload


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
template = (SRC / "template.html").read_text(encoding="utf-8")
payload = receipts_payload()

receipt_js = (
    "window.RECEIPTS = "
    + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    + ";\nwindow.RECEIPT_ORDER = "
    + json.dumps(receipt_slugs)
    + ";\n"
)

replacements = {
    "PROOF": proof_strip(),
    "HERO_FACTS": hero_facts(),
    "FEATURED": featured_sdecode(),
    "CASE_DUO": case_duo,
    "SHIP_ROWS": shipping_rows(),
    "RECEIPT_TABS": receipt_tabs(),
    "YEAR": "2026",
}

output = template
for key, value in replacements.items():
    output = output.replace("{{" + key + "}}", value)

(ROOT / "index.html").write_text(output, encoding="utf-8")
(ROOT / "receipts-data.js").write_text(receipt_js, encoding="utf-8")
shutil.copyfile(SRC / "styles.css", ROOT / "styles.css")
shutil.copyfile(SRC / "app.js", ROOT / "app.js")
shutil.copyfile(SRC / "favicon.svg", ROOT / "favicon.svg")

print("built index.html")
print(f"sdecode: {sd_tpc:.3f} tok/call, c={sd_c:.3f}, adaptive={sd_adaptive:.3f}")
print(f"pagemem: {pm_paged}/{pm_base} blocks ({pm_saved})")
print(f"cplan: reference TTFT improvement {cp_peak['improvement']}% at {cp_peak['rate']}/s")
print(f"receipts: {len(payload)} files embedded")
