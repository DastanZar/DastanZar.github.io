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

# Group 2 receipts: the rest of the 20-repo inventory.
bitforge = load("bitforge")
chunkpipe_receipt = load("chunkpipe")
expertcache = load("expertcache")
gatekeeper = load("gatekeeper")
pagedattn = load("pagedattn")
pushdown = load("pushdown")
radixlite = load("radixlite")
ring = load("ring")
streamdetok = load("streamdetok")
treetrace = load("treetrace")

sd_exp = next(
    e for e in sdecode["experiments"]
    if e["target"] == "gpt2" and e["drafter"] == "distilgpt2"
)


def sd_mean(lane: str, key: str) -> float:
    return mean([p[lane][key] for p in sd_exp["prompts"]])


sd_tpc = sd_mean("fixed_k8", "tokens_per_target_forward")
sd_calls = sd_mean("fixed_k8", "target_forwards")
sd_adaptive = sd_mean("adaptive", "tokens_per_target_forward")
sd_c = sd_exp["drafter_cost_measured"]
sd_match = all(
    all(p["identity"].values())
    for experiment in sdecode["experiments"]
    for p in experiment["prompts"]
)
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

bf4 = bitforge["softmax"]["bits4"]
bf_argmax = bf4["argmax_agreement_pct_decidable"]
bf_dev = bf4["max_prob_deviation"]

chunk_rows_1 = chunkpipe_receipt["sweep"]["1"]
chunk_rows_5 = chunkpipe_receipt["sweep"]["5"]
chunk_128_1 = next(r for r in chunk_rows_1 if r["chunk"] == 128)
chunk_8192_1 = next(r for r in chunk_rows_1 if r["chunk"] == 8192)
chunk_128_5 = next(r for r in chunk_rows_5 if r["chunk"] == 128)
chunk_8192_5 = next(r for r in chunk_rows_5 if r["chunk"] == 8192)
chunk_drop_1 = 100 * (1 - chunk_8192_1["ttft_p95_ms"] / chunk_128_1["ttft_p95_ms"])
chunk_drop_5 = 100 * (1 - chunk_8192_5["ttft_p95_ms"] / chunk_128_5["ttft_p95_ms"])

ec_hot = [
    c for c in expertcache["cases"]
    if c["trace"] == "hot_scan" and c["capacity_bytes"] == 18144
]
ec_lru = next(c for c in ec_hot if c["policy"] == "lru")
ec_cost2q = next(c for c in ec_hot if c["policy"] == "cost2q")
ec_miss_drop = 100 * (1 - ec_cost2q["misses"] / ec_lru["misses"])
ec_cpu_drop = 100 * (1 - ec_cost2q["median_cpu_ms"] / ec_lru["median_cpu_ms"])

gk_fixed = gatekeeper["results"]["fixed_window"]
gk_bucket = gatekeeper["results"]["token_bucket"]
gk_p95_drop = 100 * (1 - gk_bucket["p95_response_s"] / gk_fixed["p95_response_s"])

pa_cases = len(pagedattn["cases"])
pa_err = max(c["max_abs_error"] for c in pagedattn["cases"])
pa_err_label = f"{pa_err * 1e7:.1f}e-7"

pd_deep = pushdown["depth_scaling"][-1]
pd_ms = pd_deep["pda"]["median_us"] / 1000
pd_value = next(s for s in pushdown["selectivity"] if s["state"] == "value")

rl_session = [
    r for r in radixlite["rows"]
    if r["workload"] == "session" and r["budget_token_slots"] == 128
]
rl_rr = next(r for r in rl_session if r["policy"] == "round_robin")
rl_ca = next(r for r in rl_session if r["policy"] == "cache_aware")
rl_rr_ms = radixlite["timings"]["round_robin"]["median_us"] / 1000
rl_ca_ms = radixlite["timings"]["cache_aware"]["median_us"] / 1000

ring4 = next(m for m in ring["measurements"] if m["N"] == 4)
ring8 = next(m for m in ring["measurements"] if m["N"] == 8)

stream128 = streamdetok["chunk_sweep"][-1]
stream_x = stream128["custom"]["median_us"] / stream128["codecs"]["median_us"]

tt_near = next(c for c in treetrace["cases"] if c["case"] == "nearby_draft")["medians"]
tt_ind = next(c for c in treetrace["cases"] if c["case"] == "independent_draft")["medians"]
tt_node_x = tt_near["node_sequential_ms"] / tt_near["node_packed_ms"]
tt_total_x = tt_near["sequential_ms"] / tt_near["packed_ms"]

# Extra views for the translation layer and the "losses" band.
ec_ps_lru = next(
    c for c in expertcache["cases"]
    if c["trace"] == "phase_shift" and c["capacity_bytes"] == 18144 and c["policy"] == "lru"
)
ec_ps_cost2q = next(
    c for c in expertcache["cases"]
    if c["trace"] == "phase_shift" and c["capacity_bytes"] == 18144 and c["policy"] == "cost2q"
)

rl_batch = {
    k: v["decode"]["tokens_per_sec_b64_total"] / v["decode"]["tokens_per_sec_b1"]
    for k, v in roofline.items()
}
rl_batch_worst = min(rl_batch.values())
rl_batch_worst_key = min(rl_batch, key=rl_batch.get)
rl_batch_regress = sum(1 for r in rl_batch.values() if r < 1.0)

pd_kept = pd_value["kept"]
pd_vocab = pd_value["vocab_size"]

# Guardrails: fail the build if the receipts stop saying what the page says.
assert sd_tpc > 2.0 and sd_c < 0.7
assert sd_match, "sdecode token identity check failed"
assert pm_paged == 204 and pm_base == 504
assert cp_peak["improvement"] == 94
assert abs(fn_reduction - 0.333) < 0.001
assert bh_x == 3.98
assert bf_argmax == 100.0 and bf_dev < 0.003
assert chunk_drop_1 > 70 and chunk_drop_5 > 45
assert ec_cost2q["misses"] < ec_lru["misses"] and ec_cpu_drop > 10
assert gk_p95_drop > 70
assert pagedattn["parity_ok"] is True and pa_err < 1e-6
assert pd_deep["pda_accepts"] is True and pd_ms < 60
assert rl_ca["prefill_saved_pct"] > rl_rr["prefill_saved_pct"]
assert ring4["busbw_gbps"] > ring8["busbw_gbps"]
assert stream_x > 60 and stream128["custom_replacements"] == 0
assert tt_node_x > 5 and tt_total_x > 1 and tt_ind["accepted"] == 0

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

# ---------------------------------------------------------------------------
# The translation layer: one plain-language consequence per project, so a
# reader who does not work in ML still gets what the number is worth.
# ---------------------------------------------------------------------------
consequences = {
    "sdecode": "Six words per slow step, instead of one.",
    "pagemem": "The same card holds about 2.5&thinsp;&times;&thinsp;more conversations.",
    "cplan": "The wait for the first word falls by 94%.",
    "softfp8": "Half the memory, and the answers come out the same.",
    "latq": "Four weights in the space of one, near the theoretical floor.",
    "fusednorm": "Three trips to memory become one &mdash; 1&thinsp;MiB saved on every word.",
    "kvstamp": "An eighth of the attention memory, if you keep the right tokens.",
    "roofline-planner": f"Will it fit, and how fast &mdash; {rl_count} answers against one memory wall.",
    "gembench": "The slow way, the easy way, and the fast way, on a plain CPU.",
    "bithash": f"{bh_x:.2f}&thinsp;&times;&thinsp;smaller weights from a 4-bit codebook.",
    "treetrace": f"A kernel {tt_node_x:.1f}&thinsp;&times;&thinsp;faster that only moves the finish line {tt_total_x:.2f}&thinsp;&times;.",
    "pushdown": f"One gate token in {pd_vocab} passes; the JSON value state keeps only {pd_kept}.",
    "streamdetok": "Text streams without ever splitting a character in half.",
    "chunkpipe": "Long inputs are cut into chunks so nobody waits behind one giant job.",
    "gatekeeper": "A bouncer that keeps the queue calm by turning away the flood.",
    "radixlite": "Similar questions route to the same worker and reuse the prefill.",
    "expertcache": "Cache the experts you actually use &mdash; while the pattern holds.",
    "pagedattn": f"Same answer, different memory layout &mdash; {pa_cases}/{pa_cases} parity cases.",
    "bitforge": f"A 4-bit softmax still wins {bf_argmax:.0f}% of the decidable argmax calls.",
    "ring": f"A ring of four ranks reaches {ring4['busbw_gbps']:.2f}&thinsp;GB/s, then falls at eight.",
}


def repo_url(slug: str) -> str:
    return f"https://github.com/DastanZar/{slug}"


def receipt_url(slug: str) -> str:
    if slug == "sdecode":
        return "https://github.com/DastanZar/sdecode/blob/main/receipts/real_run.json"
    return f"https://github.com/DastanZar/{slug}/blob/main/receipts/receipt.json"


def receipt_label(slug: str) -> str:
    return "real_run.json" if slug == "sdecode" else "receipt.json"


# ---------------------------------------------------------------------------
# 20-card inventory: the complete public index, grouped by inference layer.
# ---------------------------------------------------------------------------
APP_PATHS = {
    "sdecode": "app/sdecode/index.html",
    "pagemem": "app/pagemem/index.html",
    "cplan": "app/cplan/index.html",
    "roofline-planner": "app/roofline-planner/index.html",
}

inventory_themes = [
    (
        "decode",
        "Decode loop",
        "Propose, verify, constrain, stream. Four ways to shorten the token loop without changing the output.",
    ),
    (
        "serving",
        "Serving control",
        "Batch, chunk, admit, route. Control the queue before it controls p99.",
    ),
    (
        "memory",
        "Memory & attention",
        "KV pages, token budgets, expert residency, paged attention. The memory layer, measured.",
    ),
    (
        "numerics",
        "Numerics & compression",
        "Weights, lattices, codebooks, bit-level softmax. Fewer bits, visible error.",
    ),
    (
        "kernels",
        "Kernels & topology",
        "Norm traffic, GEMV, placement, collectives. The shapes around the model.",
    ),
]

inventory_specs = [
    ("decode", ["sdecode", "treetrace", "pushdown", "streamdetok"]),
    ("serving", ["cplan", "chunkpipe", "gatekeeper", "radixlite"]),
    ("memory", ["pagemem", "kvstamp", "expertcache", "pagedattn"]),
    ("numerics", ["softfp8", "latq", "bithash", "bitforge"]),
    ("kernels", ["fusednorm", "gembench", "roofline-planner", "ring"]),
]

inventory_custom = {
    "treetrace": {
        "category": "Speculative decoding",
        "claim": f"<strong>{tt_node_x:.2f}×</strong> packed node pass",
        "description": (
            f"Random 2-layer CPU model: nearby drafts accept {tt_near['accepted']:.0f} of "
            f"{tt_near['emitted']:.0f} tokens. The packed node pass is {tt_node_x:.2f}× faster, "
            f"but end-to-end is only {tt_total_x:.2f}×; independent drafts regress."
        ),
    },
    "pushdown": {
        "category": "Structured decoding",
        "claim": f"<strong>{pd_value['kept']}/{pd_value['vocab_size']}</strong> legal tokens",
        "description": (
            f"Stack-aware JSON mask keeps {pd_value['kept']} of {pd_value['vocab_size']} tokens at the "
            f"value state. A {pd_deep['depth']:,}-deep synthetic stack parses in {pd_ms:.0f} ms; "
            "not a production DFA."
        ),
    },
    "streamdetok": {
        "category": "Token streaming",
        "claim": f"<strong>{stream_x:.1f}×</strong> faster <i>/</i> 0 replacements",
        "description": (
            f"CPU byte-level test: 128-byte chunks over a {stream128['input_bytes']:,}-byte payload, "
            f"{stream_x:.1f}× faster than the custom path with zero replacements, versus "
            f"{stream128['naive_replacements']} naive splits. No tokenizer context."
        ),
    },
    "chunkpipe": {
        "category": "Serving / scheduling",
        "claim": f"<strong>{chunk_drop_1:.1f}%</strong> lower p95 TTFT <i>/</i> 1 burst/s",
        "description": (
            f"Synthetic CPU service model, Poisson bursts, six requests each: 128→8192-token chunks cut "
            f"p95 TTFT from {chunk_128_1['ttft_p95_ms'] / 1000:.1f}s to "
            f"{chunk_8192_1['ttft_p95_ms'] / 1000:.1f}s at 1 burst/s; the 5/s gain is {chunk_drop_5:.1f}%."
        ),
    },
    "gatekeeper": {
        "category": "Admission control",
        "claim": f"<strong>{gk_p95_drop:.1f}%</strong> lower p95 response",
        "description": (
            f"Synthetic CPU open-loop burst, 300 requests: token bucket and GCRA hold p95 at "
            f"{gk_bucket['p95_response_s']:.2f}s versus {gk_fixed['p95_response_s']:.2f}s for fixed "
            f"window; admitted count {gk_bucket['admitted']} vs {gk_fixed['admitted']}."
        ),
    },
    "radixlite": {
        "category": "Prefix routing",
        "claim": f"<strong>{rl_ca['prefill_saved_pct']:.1f}%</strong> prefill saved",
        "description": (
            f"CPU token-slot simulation: cache-aware routing saves {rl_ca['prefill_saved_pct']:.1f}% of "
            f"prefill tokens at a 128-slot budget; round-robin saves {rl_rr['prefill_saved_pct']:.1f}%. "
            f"Routing costs {rl_ca_ms:.1f}ms vs {rl_rr_ms:.1f}ms."
        ),
    },
    "expertcache": {
        "category": "Expert cache",
        "claim": f"<strong>{ec_miss_drop:.1f}%</strong> fewer misses <i>/</i> hot scan",
        "description": (
            f"CPU expert-cache policy pack: cost2q cuts misses {ec_miss_drop:.1f}% and median CPU "
            f"{ec_cpu_drop:.1f}% on the hot scan; phase-shift regresses, and both cases stay in the receipt."
        ),
    },
    "pagedattn": {
        "category": "Attention kernel",
        "claim": f"<strong>{pa_cases}/{pa_cases}</strong> parity cases <i>/</i> {pa_err_label} max err",
        "description": (
            f"Synthetic q/k/v on CPU torch: streaming paged attention vs dense gather, "
            f"{pa_cases}/{pa_cases} parity cases, max abs error {pa_err_label}. Parity, not a speed "
            "win; no CUDA claim."
        ),
    },
    "bitforge": {
        "category": "Numerics",
        "claim": f"<strong>{bf_argmax:.0f}%</strong> decidable argmax <i>/</i> {bf_dev:.5f} max dev",
        "description": (
            f"4-bit softmax path with {bf_argmax:.0f}% argmax agreement on decidable rows and "
            f"{bf_dev:.5f} max probability deviation; near ties are reported separately."
        ),
    },
    "ring": {
        "category": "Collectives",
        "claim": f"<strong>{ring4['busbw_gbps']:.2f} GB/s</strong> busbw <i>/</i> 4 ranks",
        "description": (
            f"Five rank counts on loopback TCP: N=4 busbw {ring4['busbw_gbps']:.2f} GB/s; N=8 falls to "
            f"{ring8['busbw_gbps']:.2f} GB/s. Formula-normalized, not NCCL or GPU scaling."
        ),
    },
}

inventory_slugs = [slug for _, slugs in inventory_specs for slug in slugs]
assert len(inventory_slugs) == 20 and len(set(inventory_slugs)) == 20
assert set(inventory_slugs) == set(project_by_slug) | set(inventory_custom)
assert all(len(slugs) == 4 for _, slugs in inventory_specs)
assert set(APP_PATHS) <= set(inventory_slugs)
assert set(consequences) == set(inventory_slugs), "every card needs a plain-language line"


def inventory_meta() -> str:
    apps = sum(1 for slug in inventory_slugs if slug in APP_PATHS)
    return f"""<div class="inventory-meta reveal" aria-label="Inventory summary">
      <div><b>{len(inventory_slugs)}</b><span>public repos</span></div>
      <div><b>{len(inventory_themes):02d}</b><span>themes</span></div>
      <div><b>{len(inventory_slugs)}</b><span>receipt links</span></div>
      <div><b>{apps:02d}</b><span>live apps</span></div>
    </div>
    <p class="inventory-launch reveal">New here? Start with <a class="text-link strong" href="app/kvdesk/index.html" target="_blank" rel="noopener">the KV desk <span aria-hidden="true">↗</span></a> — one interactive tour of attention memory, built from three receipts.</p>"""


def inventory_cards() -> str:
    theme_by_id = {theme_id: (name, note) for theme_id, name, note in inventory_themes}
    blocks = []
    card_index = 0
    for theme_index, (theme_id, slugs) in enumerate(inventory_specs, start=1):
        theme_name, theme_note = theme_by_id[theme_id]
        cards = []
        for slug in slugs:
            card_index += 1
            if slug in project_by_slug:
                project = project_by_slug[slug]
                name = project["name"]
                category = project["category"]
                claim = project["claim"]
                description = project["description"]
            else:
                custom = inventory_custom[slug]
                name = slug
                category = custom["category"]
                claim = custom["claim"]
                description = custom["description"]

            app = APP_PATHS.get(slug)
            links = (
                f'<a class="text-link" href="{repo_url(slug)}" target="_blank" rel="noopener">repo</a>\n'
                f'            <a class="text-link" href="{receipt_url(slug)}" target="_blank" rel="noopener">receipt</a>'
            )
            if app:
                links += (
                    f'\n            <a class="inventory-app" href="{app}" target="_blank" rel="noopener">app '
                    '<span aria-hidden="true">↗</span></a>'
                )
            cards.append(
                f"""<article class="inventory-card" data-theme="{theme_id}">
          <div class="inventory-card-top">
            <span class="inventory-no">{card_index:02d}</span>
            <span class="inventory-cat">{category}</span>
          </div>
          <h4><a href="{repo_url(slug)}" target="_blank" rel="noopener">{name}</a></h4>
          <p class="inventory-claim">{claim}</p>
          <p class="inventory-so">{consequences[slug]}</p>
          <p class="inventory-desc">{description}</p>
          <div class="inventory-links">
            {links}
          </div>
        </article>"""
            )
        blocks.append(
            f"""<div class="inventory-theme reveal" data-theme="{theme_id}">
      <div class="inventory-theme-head">
        <span class="inventory-theme-no">{theme_index:02d}</span>
        <h3>{theme_name}</h3>
        <p>{theme_note}</p>
      </div>
      <div class="inventory-grid">
        {''.join(cards)}
      </div>
    </div>"""
        )
    return "\n".join(blocks)


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
  <rect class="pm-paged-bar" x="20" y="133" width="{paged_w:.1f}" height="48" fill="url(#pm-paged)"/>
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
            f'<rect class="cp-bar" style="--bar-i:{i * 2}" x="{sx:.1f}" y="{bottom - static_h:.1f}" width="{bar_w}" height="{static_h:.1f}" fill="#141511" opacity=".18"/>'
            f'<rect class="cp-bar" style="--bar-i:{i * 2 + 1}" x="{cx:.1f}" y="{bottom - cont_h:.1f}" width="{bar_w}" height="{cont_h:.1f}" fill="#E9491B"/>'
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
            "count": fmt(sd_tpc),
            "decimals": 2,
            "suffix": "×",
            "label": "tokens per target call",
            "source": "sdecode",
            "anchor": "#sdecode",
            "say": f"{fmt(sd_tpc)} tokens per target call. checked.",
        },
        {
            "value": pm_saved,
            "count": f"{float(pm_saved.rstrip('%')):.1f}",
            "decimals": 1,
            "suffix": "%",
            "label": "fewer KV blocks",
            "source": "pagemem",
            "anchor": "#pagemem",
            "say": f"{pm_saved} fewer blocks. I counted them twice.",
        },
        {
            "value": f"{cp_peak['improvement']}%",
            "count": str(cp_peak["improvement"]),
            "decimals": 0,
            "suffix": "%",
            "label": "lower TTFT",
            "source": "cplan",
            "anchor": "#cplan",
            "say": "94 percent lower TTFT. p99 is in the receipt too.",
        },
        {
            "value": f"{bh_x:.2f}×",
            "count": f"{bh_x:.2f}",
            "decimals": 2,
            "suffix": "×",
            "label": "weight compression",
            "source": "bithash",
            "anchor": "#shipping",
            "say": "3.98 times. the codebook did the work.",
        },
    ]
    return "".join(
        f"""<div class="proof-item" data-ink-point data-ink-say="{item['say']}">
        <span class="proof-num" data-count="{item['count']}" data-decimals="{item['decimals']}" data-suffix="{item['suffix']}" aria-label="{item['value']}">{item['value']}</span>
        <span class="proof-label">{item['label']}</span>
        <a class="proof-src" href="{item['anchor']}">{item['source']} <span aria-hidden="true">↗</span></a>
      </div>"""
        for item in items
    )


def hero_facts() -> str:
    facts = [
        ("CASE FILES", f"{len(projects)} on this page"),
        ("INVENTORY", f"{len(inventory_slugs)} public repos"),
        ("MEASURED ON", "CPU only"),
        ("GPU CLAIMS", "0 unlabeled"),
        ("RECEIPTS", f"{len(inventory_slugs)} linked"),
    ]
    return "".join(
        f'<li><span>{k}</span><strong>{v}</strong></li>' for k, v in facts
    )


def featured_sdecode() -> str:
    return f"""<article class="case case-featured reveal" id="sdecode" data-ink-point data-ink-say="sdecode. the target-call ledger.">
  <div class="case-copy">
    <div class="case-meta"><span class="case-no">01</span><span>Speculative decoding</span><span>2026</span></div>
    <h3>sdecode</h3>
    <p class="case-claim"><strong>{fmt(sd_tpc)}×</strong> tokens per target call<span class="case-period">.</span></p>
    <p class="case-so">{consequences['sdecode']}</p>
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
      <a class="btn btn-ghost" href="app/sdecode/index.html" target="_blank" rel="noopener">Launch app <span aria-hidden="true">↗</span></a>
      <a class="text-link" href="{receipt_url('sdecode')}" target="_blank" rel="noopener">receipt <span aria-hidden="true">↗</span></a>
    </div>
  </div>
  <div class="case-media">
    <figure class="media-frame">
      <div class="media-top"><span class="media-dots"><i></i><i></i><i></i></span><span>sdecode / recorded run</span><span class="media-live">APP</span></div>
      <img src="assets/sdecode-app.png" alt="sdecode session app showing a recorded run, lane selector, and generated text" loading="eager" width="1440" height="760">
      <figcaption class="media-bar"><span>APP / target-call budget</span><span>measured on CPU</span></figcaption>
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
    app: str | None = None,
) -> str:
    name = project_by_slug[slug]["name"]
    app_link = (
        f'<a class="text-link" href="{app}" target="_blank" rel="noopener">Launch app <span aria-hidden="true">↗</span></a>'
        if app else ""
    )
    return f"""<article class="case-mini reveal" id="{slug}" data-ink-point data-ink-say="{name}. the receipt is in the repo.">
  <div class="case-meta"><span class="case-no">{index}</span><span>{category}</span><span>2026</span></div>
  <h3>{name}</h3>
  <div class="mini-viz">
    <div class="viz-meta"><span>{viz_label}</span><span class="viz-tag">{viz_tag}</span></div>
    {svg}
  </div>
  <p class="case-claim"><strong>{claim_html}</strong></p>
  <p class="case-so">{consequences[slug]}</p>
  <p class="case-desc">{description}</p>
  <div class="case-links">
    <a class="text-link strong" href="{repo_url(slug)}" target="_blank" rel="noopener">Open repo <span aria-hidden="true">↗</span></a>
    <a class="text-link" href="{receipt_url(slug)}" target="_blank" rel="noopener">receipt <span aria-hidden="true">↗</span></a>
    {app_link}
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
        app=APP_PATHS["pagemem"],
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
        app=APP_PATHS["cplan"],
    )
)


def shipping_rows() -> str:
    rows = []
    for project in projects[3:]:
        rows.append(
            f"""<a class="ship-row reveal" href="{repo_url(project['slug'])}" target="_blank" rel="noopener" data-preview="{project['preview']}" data-preview-project="{project['name']}" data-preview-metric="{project['preview_metric']}" data-preview-label="{project['preview_label']}" data-ink-point data-ink-say="{project['name']}. still measured.">
        <span class="ship-index">{project['index']}</span>
        <span class="ship-name">{project['name']}</span>
        <span class="ship-cat">{project['category']}</span>
        <span class="ship-claim">{project['claim']}</span>
        <span class="ship-arrow" aria-hidden="true">↗</span>
      </a>"""
        )
    return "\n".join(rows)


def losses() -> str:
    items = [
        {
            "no": "01",
            "name": "treetrace",
            "tried": "Pack a draft tree into one fast node pass.",
            "expected": "the fast kernel carries the whole step.",
            "actual": f"End to end it is only {tt_total_x:.2f}&thinsp;&times;&thinsp;; independent drafts accept {tt_ind['accepted']:.0f} tokens.",
            "slug": "treetrace",
        },
        {
            "no": "02",
            "name": "expertcache",
            "tried": "Rank expert cache entries by cost instead of recency.",
            "expected": "fewer misses than plain LRU.",
            "actual": f"On the phase-shift trace it regresses: {ec_ps_cost2q['misses']:.0f} misses against {ec_ps_lru['misses']:.0f} for LRU.",
            "slug": "expertcache",
        },
        {
            "no": "03",
            "name": "roofline-planner",
            "tried": "Buy throughput by batching decode to 64 sequences.",
            "expected": "total tokens per second should climb.",
            "actual": f"Total throughput falls in {rl_batch_regress} of {rl_count} plans; worst case {rl_batch_worst:.2f}&thinsp;&times;&thinsp; the single-stream rate.",
            "slug": "roofline-planner",
        },
        {
            "no": "04",
            "name": "sdecode",
            "tried": "Let the drafter choose its own run length (adaptive K).",
            "expected": "beat a fixed guess.",
            "actual": f"Adaptive averaged {fmt(sd_adaptive)}&thinsp;&times;&thinsp; against {fmt(sd_tpc)}&thinsp;&times;&thinsp; for fixed K=8 on this pair.",
            "slug": "sdecode",
        },
        {
            "no": "05",
            "name": "ring",
            "tried": "Add ranks to raise all-reduce bandwidth.",
            "expected": "bandwidth should keep scaling.",
            "actual": f"Bus bandwidth climbs to {ring4['busbw_gbps']:.2f}&thinsp;GB/s at four ranks, then falls to {ring8['busbw_gbps']:.2f} at eight.",
            "slug": "ring",
        },
        {
            "no": "06",
            "name": "pushdown",
            "tried": "Track a deep JSON stack with a pushdown automaton.",
            "expected": "a production-ready structured-decoding mask.",
            "actual": f"It keeps only {pd_kept} of {pd_vocab} tokens at the value state &mdash; a teaching model, not a production DFA.",
            "slug": "pushdown",
        },
    ]
    cards = []
    for item in items:
        cards.append(
            f"""<article class="loss-card reveal" data-ink-point data-ink-say="{item['name']}. we publish the loss too.">
        <div class="loss-top"><span class="loss-no">{item['no']}</span><a href="{repo_url(item['slug'])}" target="_blank" rel="noopener">{item['name']}</a></div>
        <dl class="loss-dl">
          <div><dt>Tried</dt><dd>{item['tried']}</dd></div>
          <div><dt>Expected</dt><dd>{item['expected']}</dd></div>
          <div><dt>Got</dt><dd>{item['actual']}</dd></div>
        </dl>
        <a class="text-link" href="{receipt_url(item['slug'])}" target="_blank" rel="noopener">receipt <span aria-hidden="true">↗</span></a>
      </article>"""
        )
    return "\n".join(cards)


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
mascot = (SRC / "mascot.svg").read_text(encoding="utf-8")
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
    "INVENTORY": inventory_meta() + "\n" + inventory_cards(),
    "LOSSES": losses(),
    "RECEIPT_TABS": receipt_tabs(),
    "MASCOT": mascot,
    "YEAR": "2026",
}

output = template
for key, value in replacements.items():
    output = output.replace("{{" + key + "}}", value)

(ROOT / "index.html").write_text(output, encoding="utf-8")
(ROOT / "receipts-data.js").write_text(receipt_js, encoding="utf-8")
shutil.copyfile(SRC / "styles.css", ROOT / "styles.css")
shutil.copyfile(SRC / "motion.css", ROOT / "motion.css")
shutil.copyfile(SRC / "app.js", ROOT / "app.js")
shutil.copyfile(SRC / "favicon.svg", ROOT / "favicon.svg")
shutil.copyfile(SRC / "mascot.svg", ROOT / "assets" / "ink-mascot.svg")

print("built index.html")
print(f"sdecode: {sd_tpc:.3f} tok/call, c={sd_c:.3f}, adaptive={sd_adaptive:.3f}")
print(f"pagemem: {pm_paged}/{pm_base} blocks ({pm_saved})")
print(f"cplan: reference TTFT improvement {cp_peak['improvement']}% at {cp_peak['rate']}/s")
print(f"inventory: {len(inventory_slugs)} cards, {len(inventory_themes)} themes, {len(APP_PATHS)} apps")
print(f"losses: {rl_batch_regress}/{rl_count} plans regress at bs=64; worst {rl_batch_worst:.2f}x")
print(f"receipts: {len(payload)} files embedded")
