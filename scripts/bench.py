#!/usr/bin/env python3
"""Benchmark harness: run the same query set against Tavily or Linkup.

Usage:
  TAVILY_API_KEY=... python3 scripts/bench.py tavily [set]
  LINKUP_API_KEY=... python3 scripts/bench.py linkup [set]

[set] is a benchmark folder name (default: general-knowledge).
Available sets: general-knowledge, business-multilingual.

Keys may be supplied via env var, or via a key file next to this script
(tavily_key.txt / linkup_key.txt). Key files are gitignored.

Held constant across providers:
  - identical query set (data/queries.json)
  - top 10 results per query (TOP_N)
  - raw search results, no LLM-synthesized answer (retrieval apples-to-apples)
Recorded per query: latency, #results, domains, URLs, ok/err.
"""
import os, sys, json, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_SET = "general-knowledge"
MAX_RESULTS = 10
TOP_N = 10  # hard cap applied to BOTH providers -> identical result count

def get_key(env_name, file_name):
    k = os.environ.get(env_name)
    if k:
        return k.strip()
    p = os.path.join(HERE, file_name)
    if os.path.exists(p):
        k = open(p).read().strip()
        if k and "PASTE_YOUR" not in k:
            return k
    raise SystemExit(f"No {env_name}: set env var or put key in {p}")

def post(url, headers, payload, timeout=60):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode()
        return time.perf_counter() - t0, r.status, json.loads(body), None
    except urllib.error.HTTPError as e:
        return time.perf_counter() - t0, e.code, None, e.read().decode()[:400]
    except Exception as e:
        return time.perf_counter() - t0, None, None, str(e)[:400]

def run_tavily(q):
    key = get_key("TAVILY_API_KEY", "tavily_key.txt")
    dt, status, body, err = post(
        "https://api.tavily.com/search",
        {"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        {"query": q, "search_depth": "advanced", "max_results": MAX_RESULTS,
         "include_answer": False, "include_raw_content": False},
    )
    return dt, status, ((body or {}).get("results", []) if body else []), err

def run_linkup(q):
    key = get_key("LINKUP_API_KEY", "linkup_key.txt")
    dt, status, body, err = post(
        "https://api.linkup.so/v1/search",
        {"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        {"q": q, "depth": "standard", "outputType": "searchResults"},
    )
    return dt, status, ((body or {}).get("results", []) if body else []), err

def norm(results):
    out = []
    for r in results:
        content = r.get("content") or r.get("snippet") or r.get("raw_content") or ""
        out.append({"url": r.get("url", ""), "len": len(content or "")})
    return out[:TOP_N]

def domain(u):
    try:
        return urlparse(u).netloc.replace("www.", "")
    except Exception:
        return ""

def one(item, provider):
    fn = run_tavily if provider == "tavily" else run_linkup
    dt, status, results, err = fn(item["q"])
    n_raw = len(results)
    norm_r = norm(results)
    return {
        "id": item["id"], "cat": item["cat"], "q": item["q"],
        "latency_s": round(dt, 3), "status": status, "err": err,
        "n_raw": n_raw, "n_results": len(norm_r),
        "result_lens": [r["len"] for r in norm_r],
        "domains": [domain(r["url"]) for r in norm_r],
        "urls": [r["url"] for r in norm_r],
    }

def main():
    provider = sys.argv[1]
    assert provider in ("tavily", "linkup")
    dataset = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_SET
    data_dir = os.path.join(ROOT, dataset, "data")
    queries = json.load(open(os.path.join(data_dir, "queries.json")))
    with ThreadPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(lambda it: one(it, provider), queries))
    rows.sort(key=lambda r: r["id"])
    out_path = os.path.join(data_dir, f"results_{provider}.json")
    json.dump(rows, open(out_path, "w"), indent=2)

    ok = [r for r in rows if r["status"] == 200 and not r["err"]]
    lats = sorted(r["latency_s"] for r in ok)
    pct = lambda p: lats[min(len(lats) - 1, int(p * len(lats)))] if lats else 0
    print(f"\n=== {provider.upper()} — {len(ok)}/{len(rows)} ok ===")
    print(f"latency  mean={sum(lats)/len(lats):.2f}s  p50={pct(0.5):.2f}s  p90={pct(0.9):.2f}s  min={lats[0]:.2f}s  max={lats[-1]:.2f}s")
    print(f"results  mean={sum(r['n_results'] for r in ok)/len(ok):.1f}/query")
    errs = [r for r in rows if r["status"] != 200 or r["err"]]
    if errs:
        print(f"\n{len(errs)} errors:")
        for r in errs[:10]:
            print(f"  #{r['id']} [{r['status']}] {r['err']}")
    print(f"\nsaved -> {out_path}")

if __name__ == "__main__":
    main()
