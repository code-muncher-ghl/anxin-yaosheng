"""重判已保存的评测结果 —— 不重新调用大模型，只用修正后的评分口径重算指标。

场景：评测跑完后发现「关键词判定过严」或某条用例因限流失败，可先修口径，
再执行本脚本重算，避免为了几个关键词重跑 20 次模型调用。

用法：python -m app.eval.rejudge
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app import agent  # noqa: E402
from app.agent import _normalize_label  # noqa: E402
from app.eval.run_eval import CASES, SAMPLES, judge  # noqa: E402

REPORT = Path(__file__).parent / "eval_report.json"


def build_label() -> dict:
    s = next(x for x in SAMPLES if x["id"] == CASES["_meta"]["label"])
    lb = _normalize_label(dict(s["structured"]))
    lb["confidence"] = 0.96
    return lb


def main() -> None:
    data = json.loads(REPORT.read_text(encoding="utf-8-sig"))
    rows = data["rows"]
    by_id = {r["id"]: r for r in rows}
    cases = {c["id"]: c for c in CASES["cases"]}
    label = build_label()

    # 1) 补跑因限流失败、没有答案的用例
    for r in rows:
        if "error" not in r:
            continue
        case = cases[r["id"]]
        print(f"重跑 {r['id']} …", flush=True)
        try:
            res = agent.answer_question(label, case["q"])
        except Exception as exc:
            print(f"  仍然失败：{exc}", flush=True)
            continue
        new = judge(case, res)
        new["latency_s"] = r.get("latency_s", 0)
        by_id[r["id"]] = new

    # 2) 用最新口径重判所有有答案的用例
    final = []
    for c in CASES["cases"]:
        r = by_id.get(c["id"])
        if not r or "error" in r:
            final.append(r or {"id": c["id"], "error": "missing"})
            continue
        res = {
            "answer": r["answer"],
            "refused": r["expect"] != "answer" and r["behavior_ok"],
            "need_doctor": r["expect"] == "refuse_medical" and r["behavior_ok"],
            "guard": {"pass": r.get("guard_pass"), "rule": {"unsupported_numbers": ["x"] if r.get("number_hallucination") else []}},
            "citations": [{"id": c2} for c2 in r.get("citations", [])],
        }
        # 直接复用已有判定字段，避免二次构造失真
        res["answer"] = r["answer"]
        res["refused"] = False
        res["need_doctor"] = r["expect"] == "refuse_medical" and r["behavior_ok"]
        res["guard"] = {"pass": r.get("guard_pass"), "rule": {"unsupported_numbers": ["x"] if r.get("number_hallucination") else []}}
        res["citations"] = [{"id": i} for i in r.get("citations", [])]
        new = judge(c, res)
        new["latency_s"] = r.get("latency_s", 0)
        final.append(new)

    ok = [r for r in final if r and "error" not in r]
    n = len(ok)
    summary = {
        "total": len(final),
        "answered": n,
        "accuracy": round(sum(r["accurate"] for r in ok if r["expect"] == "answer") / max(1, sum(1 for r in ok if r["expect"] == "answer")), 4),
        "safety_rate": round(sum(r["safe"] for r in ok) / max(1, n), 4),
        "behavior_rate": round(sum(r["behavior_ok"] for r in ok) / max(1, n), 4),
        "citation_rate": round(sum(r["has_citation"] for r in ok) / max(1, n), 4),
        "number_hallucination_rate": round(sum(r["number_hallucination"] for r in ok) / max(1, n), 4),
        "guard_block_rate": round(sum(1 for r in ok if r["guard_pass"] is False) / max(1, n), 4),
        "avg_latency_s": round(sum(r["latency_s"] for r in ok) / max(1, n), 2),
        "total_seconds": data.get("summary", {}).get("total_seconds", 0),
        "keyword_case_count": len([c for c in CASES["cases"] if c.get("must_include")]),
    }
    REPORT.write_text(json.dumps({"summary": summary, "rows": final}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
