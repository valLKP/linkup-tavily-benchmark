# Linkup vs. Tavily — Search Latency Benchmark

An independent, reproducible latency benchmark comparing the **Linkup** and **Tavily**
web-search APIs. Two query sets are included:

| Set | Queries | Focus | Result |
|---|---|---|---|
| [`general-knowledge`](./general-knowledge/QUESTIONS.md) | 100 | European general-knowledge + LinkedIn extraction | **Linkup 2.5× faster, 100/100** |
| [`business-multilingual`](./business-multilingual/QUESTIONS.md) | 50 | European business (EN) + German-language (DE) | **Linkup 2.1× faster, 50/50** |

## TL;DR

Across both sets, **Linkup is faster on every single query** and shows no penalty on
German-language queries.

- **General knowledge (100 q):** Linkup 2.5× faster on average — mean **1.59s** vs **4.02s**
  (median 1.59s vs 4.00s). Faster on **100/100** queries.
- **Business & German (50 q):** Linkup 2.1× faster on average — mean **1.90s** vs **4.07s**
  (median 1.82s vs 4.14s). Faster on **50/50** queries. **Same latency in English and German.**

## Method (both sets)

- **Identical inputs** sent to both APIs. Results **capped to the top 10** per query so the
  comparison is like-for-like.
- Comparable configuration: raw search results, no LLM-synthesized answer.
  Tavily `search_depth="advanced"`, Linkup `depth="standard"`, `outputType="searchResults"`.
- **Cache controlled.** Every query set is fresh and was never replayed — repeating identical
  queries triggers provider-side caching and produces artificially low latencies. All numbers
  reflect cold, cache-free performance.
- Each provider run **sequentially** (not concurrently) to avoid network/CPU contention
  skewing the timing. Requests within a run issued with a fixed concurrency of 6 workers,
  identical for both providers.
- Measured wall-clock time is end-to-end HTTP round-trip from the client.

---

## Set 1 — General knowledge (100 queries)

| Metric | Tavily | Linkup |
|---|---|---|
| Mean latency | 4.02s | **1.59s** |
| Median (p50) | 4.00s | **1.59s** |
| p90 | 5.53s | **2.05s** |
| Max | 6.63s | **4.38s** |
| Fastest per query | 0/100 | **100/100** |

**Linkup 2.5× faster on average.** It is also more predictable: its slowest query (4.38s)
beats Tavily's *median* (4.00s) — over half of Tavily's queries are slower than Linkup's
worst case.

| Category | Tavily | Linkup | Speed-up |
|---|---|---|---|
| history | 4.14s | **1.65s** | 2.5× |
| art & literature | 3.74s | **1.27s** | 2.9× |
| geography | 3.85s | **1.70s** | 2.3× |
| science | 4.08s | **1.65s** | 2.5× |
| food | 4.38s | **1.49s** | 2.9× |
| music | 3.87s | **1.37s** | 2.8× |
| sports | 3.61s | **1.58s** | 2.3× |
| cinema | 3.39s | **1.15s** | 2.9× |
| EU institutions | 3.68s | **1.67s** | 2.2× |
| architecture | 4.60s | **1.43s** | 3.2× |
| LinkedIn | 5.27s | **2.77s** | 1.9× |

**Source complementarity:** the two engines agree on only **24%** of domains (mean Jaccard),
~3.0 shared domains per query, 88/100 queries with ≥1 shared domain.

**LinkedIn extraction:** 6 queries target LinkedIn URLs. Linkup performs structured LinkedIn
extraction (profile / posts as clean structured data); Tavily has no dedicated LinkedIn
capability and falls back to a generic web search of pages mentioning the URL.

---

## Set 2 — Business & German-language (50 queries)

35 European business queries (English) + 15 German-language queries.

| Metric | Tavily | Linkup |
|---|---|---|
| Mean latency | 4.07s | **1.90s** |
| Median (p50) | 4.14s | **1.82s** |
| p90 | 5.44s | **2.43s** |
| Max | 5.77s | **2.69s** |
| Fastest per query | 0/50 | **50/50** |

**Linkup 2.1× faster on average.**

**No German-language penalty** — Linkup answers English and German queries at the same speed,
while Tavily is slightly slower in German:

| Sub-set | Tavily | Linkup | Speed-up |
|---|---|---|---|
| Business (English, 35) | 4.00s | **1.90s** | 2.1× |
| German (Deutsch, 15) | 4.25s | **1.90s** | 2.2× |

| Category | Tavily | Linkup | Speed-up |
|---|---|---|---|
| funding | 4.56s | **2.29s** | 2.0× |
| financials | 3.59s | **1.89s** | 1.9× |
| leadership | 3.61s | **1.73s** | 2.1× |
| M&A | 4.93s | **1.84s** | 2.7× |
| market | 4.21s | **1.82s** | 2.3× |
| B2B | 3.18s | **1.64s** | 1.9× |
| german | 4.25s | **1.90s** | 2.2× |

**Source complementarity:** on these specialized business/DACH topics the engines diverge even
more — only **16%** domain overlap (mean Jaccard), ~2.4 shared domains per query, 46/50 queries
with ≥1 shared domain.

---

## Scope

This benchmark measures **latency**, **source complementarity**, and **LinkedIn extraction
capability**. It does not score answer *relevance* or *quality* — that is a separate,
subjective evaluation and is out of scope here.

## Reproduce it

```bash
# 1. Provide API keys (env vars or key files in scripts/)
export TAVILY_API_KEY=...
export LINKUP_API_KEY=...

# 2. Run a set (default: general-knowledge). Run each provider sequentially.
python3 scripts/bench.py tavily general-knowledge
python3 scripts/bench.py linkup general-knowledge
python3 scripts/report.py general-knowledge

python3 scripts/bench.py tavily business-multilingual
python3 scripts/bench.py linkup business-multilingual
python3 scripts/report.py business-multilingual
```

Each set stores its raw per-query results in `<set>/data/`: `results_tavily.json`,
`results_linkup.json`, and `latency_per_query.csv`. The result files are written by
`scripts/bench.py` and match its output schema exactly, so a re-run reproduces the same
format (latency values will differ slightly with network conditions).
