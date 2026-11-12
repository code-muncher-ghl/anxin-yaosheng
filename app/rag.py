"""检索层：说明书写入 → 切块 → 混合检索（BM25 + 章节先验 + 关键词扩展）

为什么不用向量库：
- 单张说明书的语料只有 1~3k 字，BM25 在中文短文本上的召回足够；
- 演示环境不依赖任何外部 embedding 服务，离线可跑，答辩现场不怕断网；
- 接口与 `VectorRetriever` 保持一致，后续接 bge-m3 / text-embedding-3 只需替换 `retrieve`。
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

try:  # 中文分词优先，缺失时退化为字符二元组
    import jieba

    jieba.setLogLevel(20)

    def tokenize(text: str) -> list[str]:
        words = [w.strip() for w in jieba.lcut(text) if w.strip()]
        grams = [text[i : i + 2] for i in range(len(text) - 1)]
        return words + grams

except Exception:  # pragma: no cover
    def tokenize(text: str) -> list[str]:
        return [text[i : i + 2] for i in range(len(text) - 1)]


KB_PATH = Path(__file__).resolve().parent / "kb" / "interactions.json"
KB = json.loads(KB_PATH.read_text(encoding="utf-8-sig"))

SECTION_LABEL = {
    "indications": "适应症",
    "dosage": "用法用量",
    "contraindications": "禁忌",
    "adverse_reactions": "不良反应",
    "precautions": "注意事项",
    "interactions": "药物相互作用",
    "storage": "贮藏",
    "special_populations": "特殊人群用药",
}

# 口语 → 书面语 的同义归一，解决「一天吃几次」检索不到「一日1次」的问题
SYNONYMS = {
    "一天": "一日", "每天": "一日", "每日": "一日", "天天": "一日",
    "吃": "服用", "喝": "服用", "吃药": "服药",
    "几片": "一次 片", "多少片": "一次 片", "几次": "一日 次",
    "副作用": "不良反应", "副反应": "不良反应",
    "不能吃": "禁忌", "什么人不能": "禁忌",
    "一起": "相互作用", "同吃": "相互作用", "同服": "相互作用",
    "放": "贮藏", "保存": "贮藏", "冰箱": "贮藏",
    "孕妇": "妊娠", "怀孩子": "妊娠",
    "老人": "老年", "爸妈": "老年",
}


def expand_query(query: str) -> str:
    """把口语问题扩展成「原句 + 书面语同义词」，提升 BM25 召回。"""
    extra = [v for k, v in SYNONYMS.items() if k in query]
    return query + (" " + " ".join(extra) if extra else "")

# 问题意图 → 章节先验，用于轻量 query 理解
INTENT_PRIOR = {
    "dosage": (["怎么吃", "吃几片", "几次", "饭前", "饭后", "空腹", "剂量", "一天", "多久", "疗程", "顿服"], 0.22),
    "contraindications": (["禁忌", "能不能吃", "不能", "禁用", "怀孕", "肝", "肾"], 0.20),
    "adverse_reactions": (["副作用", "不良反应", "不舒服", "头晕", "恶心", "皮疹", "肌肉"], 0.20),
    "interactions": (["一起吃", "同服", "相互作用", "还能吃", "冲突", "联用"], 0.22),
    "indications": (["治什么", "干什么", "有什么用", "适应症", "主治"], 0.18),
    "precautions": (["注意", "当心", "忌口", "喝酒", "开车", "储存", "放", "漏服", "漏吃", "忘记", "漏了", "掰开", "嚼碎"], 0.14),
    "special_populations": (["老人", "老年", "小孩", "儿童", "孕妇", "哺乳"], 0.16),
}


@dataclass
class Chunk:
    cid: int
    label_id: str
    section: str
    text: str
    tokens: list[str] = field(default_factory=list)


def build_chunks(label: dict) -> list[Chunk]:
    """把结构化说明书拆成「一章节一 chunk，一句一条」的最小证据单元。"""
    chunks: list[Chunk] = []
    drug = label.get("drug_name") or "本药"
    if label.get("spec"):
        chunks.append(Chunk(0, label["id"], "basic", f"{drug}，规格：{label['spec']}"))
    for key, cn in SECTION_LABEL.items():
        items = label.get(key) or []
        if isinstance(items, str):  # storage 等字段是字符串，必须当作一条，而不是逐字拆
            items = [items]
        for item in items:
            if not item:
                continue
            chunks.append(Chunk(0, label["id"], key, f"【{cn}】{item}"))
    for cid, c in enumerate(chunks, start=1):
        c.cid = cid
        c.tokens = tokenize(c.text)
    return chunks


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.docs = docs
        self.k1, self.b = k1, b
        self.n = len(docs)
        self.avgdl = sum(len(d) for d in docs) / max(self.n, 1)
        self.df: dict[str, int] = {}
        for d in docs:
            for t in set(d):
                self.df[t] = self.df.get(t, 0) + 1
        self.tf: list[dict[str, int]] = []
        for d in docs:
            freq: dict[str, int] = {}
            for t in d:
                freq[t] = freq.get(t, 0) + 1
            self.tf.append(freq)

    def idf(self, term: str) -> float:
        n_q = self.df.get(term, 0)
        return math.log(1 + (self.n - n_q + 0.5) / (n_q + 0.5))

    def score(self, query_tokens: list[str], i: int) -> float:
        s, dl = 0.0, len(self.docs[i])
        for t in query_tokens:
            f = self.tf[i].get(t, 0)
            if not f:
                continue
            s += self.idf(t) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / max(self.avgdl, 1)))
        return s


class Retriever:
    """一本说明书一个检索器；知识库（老年用药常识 + 相互作用）单独参与召回。"""

    def __init__(self, label: dict) -> None:
        self.label = label
        self.chunks = build_chunks(label)
        self.bm25 = BM25([c.tokens for c in self.chunks]) if self.chunks else None

    # ------------------------------------------------------------- 章节先验
    @staticmethod
    def _prior(query: str) -> dict[str, float]:
        prior: dict[str, float] = {}
        for section, (kws, w) in INTENT_PRIOR.items():
            if any(k in query for k in kws):
                prior[section] = w
        return prior

    # --------------------------------------------------------------- 主检索
    def retrieve(self, query: str, top_k: int = 4) -> list[Chunk]:
        if not self.chunks or not self.bm25:
            return []
        q_tokens = tokenize(expand_query(query))
        prior = self._prior(query)
        scored: list[tuple[float, Chunk]] = []
        for i, c in enumerate(self.chunks):
            s = self.bm25.score(q_tokens, i)
            s += prior.get(c.section, 0.0) * 2.0
            if c.section == "basic":
                s *= 0.6
            if s > 0:
                scored.append((s, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        if not scored:  # 兜底：返回最相关的章节（用法用量 + 禁忌）
            fallback = [c for c in self.chunks if c.section in ("dosage", "contraindications")][:2]
            return fallback
        top = scored[0][0]
        picked = [c for s, c in scored[:top_k] if s >= top * 0.35]
        return picked or [scored[0][1]]

    # ------------------------------------------------------- 知识库召回
    @staticmethod
    def kb_lookup(drug_names: list[str]) -> list[dict]:
        hits: list[dict] = []
        for e in KB["entries"]:
            for a in drug_names:
                for b in drug_names:
                    if a == b:
                        continue
                    if (e["a"] in a or a in e["a"]) and (e["b"] in b or b in e["b"]):
                        if e not in hits:
                            hits.append(e)
        return hits

    @staticmethod
    def elderly_tips(query: str = "", top_k: int = 3) -> list[dict]:
        tips = KB["elderly_precautions"]
        if not query:
            return tips[:top_k]
        # 口语 → 常识条目的关键词映射，解决「漏吃了」匹配不到「漏服处理」的问题
        SYNONYMS = {
            "EP04": ["漏", "忘", "补服", "少吃", "错过"],
            "EP01": ["剂量", "起始", "多少", "加量", "减量"],
            "EP02": ["早上", "晚上", "睡前", "饭前", "饭后", "什么时候", "几点"],
            "EP03": ["一起", "多种", "几种药", "同时吃"],
            "EP05": ["掰", "碾", "碎", "吞", "卡"],
            "EP06": ["放", "保存", "温度", "冰箱", "过期"],
            "EP07": ["复诊", "看病", "带什么"],
            "EP08": ["黑便", "瘀斑", "尿", "皮疹", "严不严重", "危险"],
        }
        q_tokens = set(tokenize(query))
        scored = []
        for t in tips:
            overlap = len(q_tokens & set(tokenize(t["title"] + t["text"])))
            bonus = sum(1 for kw in SYNONYMS.get(t["id"], []) if kw in query) * 3
            scored.append((overlap + bonus, t))
        scored.sort(key=lambda x: x[0], reverse=True)
        picked = [t for s, t in scored[:top_k] if s > 0]
        return picked or tips[:2]


def evidence_block(chunks: list[Chunk], tips: list[dict] | None = None, kb_hits: list[dict] | None = None) -> str:
    """把召回结果拼成带编号的证据块，编号即前端引用的锚点。"""
    lines, idx = [], 0
    for c in chunks:
        idx += 1
        lines.append(f"[{idx}] {c.text}")
    if tips:
        for t in tips:
            idx += 1
            lines.append(f"[{idx}] 【老年用药常识·{t['title']}】{t['text']}")
    if kb_hits:
        for e in kb_hits:
            idx += 1
            lines.append(f"[{idx}] 【相互作用知识库·{e['id']}】{e['a']} + {e['b']}：{e['mechanism']} 后果：{e['consequence']}")
    return "\n".join(lines) if lines else "（无证据）"

