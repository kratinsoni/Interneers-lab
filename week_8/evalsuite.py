"""
eval_suite.py
-------------
Evaluation suite for the RAG retrieval pipeline.

Metrics evaluated per query
────────────────────────────
  - Source Hit   : At least one retrieved chunk comes from the expected source document.
  - Top-1 Hit    : The BEST chunk (rank 1) is from the expected source.
  - Avg Score    : Mean similarity score across returned chunks (lower = more relevant
                   for cosine / L2 distance from ChromaDB).
  - Keyword Hit  : At least one chunk contains a key phrase expected in the answer.

Usage:
    python eval_suite.py
"""

import json
import sys
from rag_pipeline import retrieve_relevant_chunks, load_vectorstore, ingest_all
from pathlib import Path

# ── Eval dataset ─────────────────────────────────────────────────────────────
# Format:
#   query           : the question asked
#   expected_source : stem of the .txt filename that should be retrieved
#   keywords        : at least one of these phrases must appear in a retrieved chunk
# ──────────────────────────────────────────────────────────────────────────────
EVAL_CASES = [
    {
        "id": "ret_01",
        "query": "What's the return policy for damaged items?",
        "expected_source": "return_policy",
        "keywords": ["damaged", "DOA", "prepaid", "photograph", "48 hours"],
    },
    {
        "id": "ret_02",
        "query": "How do I return a defective product?",
        "expected_source": "return_policy",
        "keywords": ["defective", "warranty@buildright", "proof of purchase", "repair"],
    },
    {
        "id": "ret_03",
        "query": "Can I return an opened science kit?",
        "expected_source": "return_policy",
        "keywords": ["consumable", "chemical", "non-returnable", "safety"],
    },
    {
        "id": "ret_04",
        "query": "What is the warranty period for the Lego Castle?",
        "expected_source": "product_manual",
        "keywords": ["2-year", "warranty", "Lego Castle", "defects"],
    },
    {
        "id": "ret_05",
        "query": "How long is the warranty on the RC Racing Car?",
        "expected_source": "product_manual",
        "keywords": ["1-year", "RC Racing", "manufacturing defects"],
    },
    {
        "id": "ret_06",
        "query": "What are the payment terms for vendors?",
        "expected_source": "vendor_faq",
        "keywords": ["Net-45", "payment", "invoice", "2/10"],
    },
    {
        "id": "ret_07",
        "query": "What is the minimum order quantity for new suppliers?",
        "expected_source": "vendor_faq",
        "keywords": ["500 units", "MOQ", "minimum order"],
    },
    {
        "id": "ret_08",
        "query": "How do I get a refund as store credit?",
        "expected_source": "return_policy",
        "keywords": ["store credit", "refund", "gift"],
    },
    {
        "id": "ret_09",
        "query": "What safety certifications do toy vendors need?",
        "expected_source": "vendor_faq",
        "keywords": ["ASTM F963", "EN71", "FCC", "certification"],
    },
    {
        "id": "ret_10",
        "query": "How do I replace missing pieces from a set?",
        "expected_source": "product_manual",
        "keywords": ["replacement", "missing", "hotline", "parts"],
    },
]


# ── Evaluation logic ──────────────────────────────────────────────────────────


def evaluate_case(case: dict, vectorstore, top_k: int = 3) -> dict:
    chunks = retrieve_relevant_chunks(
        case["query"], top_k=top_k, vectorstore=vectorstore
    )

    sources = [c["source"] for c in chunks]
    contents_all = " ".join(c["content"].lower() for c in chunks)
    scores = [c["score"] for c in chunks]

    source_hit = case["expected_source"] in sources
    top1_hit = bool(sources) and sources[0] == case["expected_source"]
    keyword_hit = any(kw.lower() in contents_all for kw in case["keywords"])
    avg_score = round(sum(scores) / len(scores), 4) if scores else None

    return {
        "id": case["id"],
        "query": case["query"],
        "expected_source": case["expected_source"],
        "retrieved_sources": sources,
        "source_hit": source_hit,
        "top1_hit": top1_hit,
        "keyword_hit": keyword_hit,
        "avg_score": avg_score,
        "pass": source_hit and keyword_hit,
    }


def run_eval_suite(top_k: int = 3, verbose: bool = True) -> dict:
    chroma_dir = Path(__file__).parent / "chroma_db"

    # Auto-ingest if the DB doesn't exist yet
    if not chroma_dir.exists() or not any(chroma_dir.iterdir()):
        print("[Eval] ChromaDB not found — running ingestion first…")
        vs = ingest_all()
    else:
        vs = load_vectorstore()

    results = []
    for case in EVAL_CASES:
        r = evaluate_case(case, vs, top_k=top_k)
        results.append(r)

    # ── Summary ────────────────────────────────────────────────────────────────
    n = len(results)
    source_hits = sum(r["source_hit"] for r in results)
    top1_hits = sum(r["top1_hit"] for r in results)
    kw_hits = sum(r["keyword_hit"] for r in results)
    passes = sum(r["pass"] for r in results)

    summary = {
        "total_cases": n,
        "source_hit_rate": round(source_hits / n, 2),
        "top1_hit_rate": round(top1_hits / n, 2),
        "keyword_hit_rate": round(kw_hits / n, 2),
        "overall_pass_rate": round(passes / n, 2),
    }

    if verbose:
        _print_results(results, summary)

    return {"summary": summary, "results": results}


def _print_results(results: list[dict], summary: dict):
    PASS = "✅ PASS"
    FAIL = "❌ FAIL"
    SEP = "─" * 70

    print(f"\n{'='*70}")
    print("  RETRIEVAL EVAL SUITE — BuildRight Knowledge Base")
    print(f"{'='*70}")

    for r in results:
        status = PASS if r["pass"] else FAIL
        print(f"\n{SEP}")
        print(f"[{r['id']}] {status}")
        print(f"  Query    : {r['query']}")
        print(f"  Expected : {r['expected_source']}")
        print(f"  Got      : {r['retrieved_sources']}")
        print(
            f"  Source✓  : {'Yes' if r['source_hit'] else 'No'}  |  "
            f"Top-1✓: {'Yes' if r['top1_hit'] else 'No'}  |  "
            f"Keyword✓: {'Yes' if r['keyword_hit'] else 'No'}  |  "
            f"Avg Score: {r['avg_score']}"
        )

    print(f"\n{'='*70}")
    print("  SUMMARY")
    print(f"{'='*70}")
    print(f"  Total Cases        : {summary['total_cases']}")
    print(f"  Source Hit Rate    : {summary['source_hit_rate']*100:.0f}%")
    print(f"  Top-1 Hit Rate     : {summary['top1_hit_rate']*100:.0f}%")
    print(f"  Keyword Hit Rate   : {summary['keyword_hit_rate']*100:.0f}%")
    print(f"  Overall Pass Rate  : {summary['overall_pass_rate']*100:.0f}%")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    output = run_eval_suite(top_k=3, verbose=True)
    # Optionally save results to JSON
    out_path = Path(__file__).parent / "eval_results.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"[Eval] Results saved to {out_path}")
