"""冒烟测试：不依赖网络与大模型，验证核心逻辑正确性。

用法：
    python -m tests.test_smoke        # 直接运行
    pytest tests/                     # 也兼容 pytest
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agent import _normalize_label  # noqa: E402
from app.guard import check_citations, check_numbers, risk_scan  # noqa: E402
from app.rag import Retriever, build_chunks, expand_query  # noqa: E402
from app.tts import normalize_for_tts  # noqa: E402

SAMPLES = json.loads((ROOT / "app" / "kb" / "samples.json").read_text(encoding="utf-8-sig"))["samples"]


def _label(sample_id: str = "lipitor") -> dict:
    s = next(x for x in SAMPLES if x["id"] == sample_id)
    lb = _normalize_label(dict(s["structured"]))
    lb["confidence"] = 0.96
    return lb


def test_normalize_label():
    lb = _label()
    assert lb["drug_name"] == "阿托伐他汀钙片"
    assert isinstance(lb["dosage"], list) and lb["dosage"]
    assert 0 <= lb["confidence"] <= 1
    assert lb["id"].startswith("lb_")


def test_chunks_cover_sections():
    lb = _label()
    chunks = build_chunks(lb)
    sections = {c.section for c in chunks}
    for s in ("dosage", "contraindications", "adverse_reactions", "interactions"):
        assert s in sections, f"缺少章节 {s}"
    # storage 是字符串字段，必须整体成块，不能被逐字拆开
    storage = [c for c in chunks if c.section == "storage"]
    assert len(storage) == 1
    assert "干燥" in storage[0].text


def test_bm25_retrieval_hits_dosage():
    lb = _label()
    r = Retriever(lb)
    got = r.retrieve("一天吃几次")
    assert got, "检索为空"
    assert any(c.section == "dosage" for c in got), [c.section for c in got]
    assert any("一日1次" in c.text for c in got), [c.text[:20] for c in got]


def test_synonym_expansion():
    q = expand_query("这个药一天吃几次")
    assert "一日" in q and "服用" in q


def test_kb_interaction_lookup():
    hits = Retriever.kb_lookup(["阿托伐他汀钙片", "克拉霉素片"])
    assert hits, "应命中阿托伐他汀 + 克拉霉素"
    assert hits[0]["level"] == "严重"


def test_elderly_tip_for_missed_dose():
    tips = Retriever.elderly_tips("漏吃了一次怎么办", top_k=2)
    assert any("漏服" in t["title"] for t in tips), tips


def test_guard_number_grounding():
    evidence = "【用法用量】一次1片（20mg），一日1次。"
    assert check_numbers("一次吃1片，一日1次。[1]", evidence) == []
    bad = check_numbers("一次吃2片，一日3次。[1]", evidence)
    assert bad, "编造的剂量必须被识别"


def test_guard_citation_and_risk():
    assert check_citations("见 [1] 和 [3]", 3) == []
    assert check_citations("见 [5]", 3) == [5]
    assert risk_scan("您可以停药了")
    assert not risk_scan("请咨询医生是否可以停药")


def test_tts_normalization():
    out = normalize_for_tts("一次1片（20mg），一日1次，0.25g")
    assert "二十毫克" in out
    assert "零点二五克" in out
    assert "一日一次" in out
    assert "20" not in out and "mg" not in out


def test_demo_label_roundtrip():
    lb = _label("klaricid")
    assert lb["drug_name"] == "克拉霉素片"
    chunks = build_chunks(lb)
    assert any("饭后" in c.text for c in chunks if c.section == "dosage")


def main() -> None:
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL  {name}  ->  {exc}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  ERROR {name}  ->  {type(exc).__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
