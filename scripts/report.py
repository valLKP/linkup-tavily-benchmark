#!/usr/bin/env python3
"""Regenerate the latency report (markdown tables + per-query CSV) from raw results.

Usage:  python3 scripts/report.py
Reads:  data/results_tavily.json, data/results_linkup.json
Writes: data/latency_per_query.csv  and prints markdown tables to stdout.
"""
import os, sys, json, csv, statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = sys.argv[1] if len(sys.argv) > 1 else "general-knowledge"
DATA = os.path.join(ROOT, DATASET, "data")
T = {r["id"]: r for r in json.load(open(os.path.join(DATA, "results_tavily.json")))}
L = {r["id"]: r for r in json.load(open(os.path.join(DATA, "results_linkup.json")))}
ids = sorted(set(T) & set(L))
print(f"# Dataset: {DATASET}\n")

def stats(vals):
    v = sorted(vals)
    p = lambda q: v[min(len(v) - 1, int(q * len(v)))]
    return dict(mean=st.mean(v), p50=p(0.5), p90=p(0.9), mn=v[0], mx=v[-1])

st_t = stats([T[i]["latency_s"] for i in ids])
st_l = stats([L[i]["latency_s"] for i in ids])
speedup = st_t["mean"] / st_l["mean"]

print("## Latency — overall (n=%d queries)\n" % len(ids))
print("| Metric | Tavily | Linkup |")
print("|---|---|---|")
print(f"| Mean | {st_t['mean']:.2f}s | **{st_l['mean']:.2f}s** |")
print(f"| Median (p50) | {st_t['p50']:.2f}s | **{st_l['p50']:.2f}s** |")
print(f"| p90 | {st_t['p90']:.2f}s | **{st_l['p90']:.2f}s** |")
print(f"| Min | {st_t['mn']:.2f}s | **{st_l['mn']:.2f}s** |")
print(f"| Max | {st_t['mx']:.2f}s | **{st_l['mx']:.2f}s** |")
wins = sum(1 for i in ids if L[i]["latency_s"] < T[i]["latency_s"])
print(f"| Fastest per query | {len(ids)-wins}/{len(ids)} | **{wins}/{len(ids)}** |")
print(f"\n**Linkup is {speedup:.1f}× faster on average.**\n")

print("## Latency — by category\n")
cats = {}
for i in ids:
    cats.setdefault(T[i]["cat"], []).append(i)
print("| Category | Tavily (mean) | Linkup (mean) | Speed-up |")
print("|---|---|---|---|")
for c, cid in cats.items():
    tl = st.mean(T[i]["latency_s"] for i in cid)
    ll = st.mean(L[i]["latency_s"] for i in cid)
    print(f"| {c} | {tl:.2f}s | **{ll:.2f}s** | {tl/ll:.1f}× |")

print("\n## Source complementarity\n")
jac, shared = [], []
for i in ids:
    td = set(d for d in T[i]["domains"] if d)
    ld = set(d for d in L[i]["domains"] if d)
    union = td | ld
    jac.append(len(td & ld) / len(union) if union else 0)
    shared.append(len(td & ld))
print(f"- Mean domain overlap (Jaccard): **{st.mean(jac):.2f}** "
      f"(0 = fully different sources, 1 = identical)")
print(f"- Mean shared domains per query: {st.mean(shared):.1f}")
print(f"- Queries sharing >=1 domain: {sum(1 for c in shared if c)}/{len(ids)}")

# per-query CSV
csv_path = os.path.join(DATA, "latency_per_query.csv")
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "category", "question", "tavily_latency_s", "linkup_latency_s", "faster"])
    for i in ids:
        faster = "linkup" if L[i]["latency_s"] < T[i]["latency_s"] else "tavily"
        w.writerow([i, T[i]["cat"], T[i]["q"], T[i]["latency_s"], L[i]["latency_s"], faster])
print(f"\n_CSV written: {DATASET}/data/latency_per_query.csv_")
