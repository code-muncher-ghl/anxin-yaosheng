"""Agent 编排层

三段式：
  Planner（模型自己决定要不要调工具）
    → Tool 执行（检索 / 相互作用知识库 / 老年用药常识 / 转人工）
      → 带证据生成 + 自检复核

与「一问一答套壳」的区别：模型的输出不是最终答案，而是「下一步动作」，
工具返回的证据再进入 Prompt，形成闭环；全过程有 trace，可审计。
"""
from __future__ import annotations

import json
import re
import time
import uuid
from typing import Any

from . import config, prompts
from .guard import verify
from .llm import LLMError, llm
from .rag import Retriever, evidence_block

# --------------------------------------------------------------- 工具定义
TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_label",
            "description": "在当前药品说明书中检索证据片段。任何涉及用法、禁忌、副作用的问题都必须先调用它。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词，例如 用法用量 饭前 副作用"},
                    "top_k": {"type": "integer", "description": "返回条数，默认 4"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_interaction",
            "description": "查询两种药之间是否存在相互作用，返回风险等级与机制。",
            "parameters": {
                "type": "object",
                "properties": {
                    "drug_a": {"type": "string"},
                    "drug_b": {"type": "string"},
                },
                "required": ["drug_a", "drug_b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_elderly_tip",
            "description": "查询老年人用药常识，例如起始剂量、漏服处理、多重用药。",
            "parameters": {
                "type": "object",
                "properties": {"topic": {"type": "string", "description": "主题关键词"}},
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_med_reminder",
            "description": "为用户生成用药提醒计划（每天几点吃药）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "drug": {"type": "string"},
                    "times": {"type": "array", "items": {"type": "string"}, "description": "24小时制时间，如 08:00"},
                    "note": {"type": "string", "description": "饭前/饭后等提示"},
                },
                "required": ["drug", "times"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "当问题涉及停药、换药、加量、诊断，或证据不足时，转人工药师。",
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
                "required": ["reason"],
            },
        },
    },
]


def new_id(prefix: str = "lb") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ------------------------------------------------------------ 1. 解析说明书
def parse_from_image(image_bytes: bytes, mime: str) -> dict:
    t0 = time.time()
    data = llm.vision_json(image_bytes, prompts.PARSE_PROMPT, mime=mime, temperature=0.0, max_tokens=2000)
    label = _normalize_label(data)
    label["_meta"] = {"source": "vision", "ms": int((time.time() - t0) * 1000)}
    return label


def parse_from_text(text: str) -> dict:
    t0 = time.time()
    data = llm.json(
        [
            {"role": "system", "content": prompts.SYSTEM_PERSONA},
            {"role": "user", "content": prompts.PARSE_PROMPT + f"\n\n【说明书文字】\n{text}"},
        ],
        temperature=0.0,
        max_tokens=2000,
    )
    label = _normalize_label(data)
    label["_meta"] = {"source": "text", "ms": int((time.time() - t0) * 1000)}
    return label


def _normalize_label(data: dict) -> dict:
    list_fields = ["indications", "dosage", "contraindications", "adverse_reactions", "precautions", "interactions", "special_populations"]
    out: dict[str, Any] = {
        "id": new_id(),
        "drug_name": (data.get("drug_name") or "").strip(),
        "spec": (data.get("spec") or "").strip(),
        "storage": (data.get("storage") or "").strip(),
        "evidence": data.get("evidence") or {},
        "confidence": float(data.get("confidence") or 0.0),
        "raw": data,
    }
    for f in list_fields:
        v = data.get(f) or []
        if isinstance(v, str):
            v = [v]
        out[f] = [str(x).strip() for x in v if str(x).strip()]
    if out["confidence"] >= 1:  # 有些模型用百分制
        out["confidence"] = out["confidence"] / 100
    return out


# ------------------------------------------------------------ 2. 语音播报稿
def make_script(label: dict) -> dict:
    payload = {k: label[k] for k in ("drug_name", "spec", "indications", "dosage", "contraindications", "adverse_reactions", "precautions")}
    data = llm.json(
        [
            {"role": "system", "content": prompts.SYSTEM_PERSONA},
            {"role": "user", "content": prompts.EXPLAIN_PROMPT.format(label_json=json.dumps(payload, ensure_ascii=False, indent=1))},
        ],
        temperature=0.3,
        max_tokens=1200,
    )
    segments = data.get("segments") or []
    # 数字护栏：播报稿里的数字必须来自结构化字段
    src = json.dumps(payload, ensure_ascii=False)
    from .guard import check_numbers

    for seg in segments:
        bad = check_numbers(seg.get("text", ""), src)
        if bad:
            seg["warn"] = f"以下数字未在说明书中找到：{', '.join(bad)}"
    text = "".join(s.get("text", "") for s in segments)
    return {
        "segments": segments,
        "safety_note": data.get("safety_note") or config.DISCLAIMER,
        "script": text,
        "chars": len(text),
        "est_seconds": round(len(text) / 4.2),  # 中文慢速播报约 4.2 字/秒
    }


# ------------------------------------------------------------ 3. 证据问答
def answer_question(label: dict, question: str, top_k: int = 4) -> dict:
    retriever = Retriever(label)
    chunks = retriever.retrieve(question, top_k=top_k)
    tips = Retriever.elderly_tips(question, top_k=2)
    evidence = evidence_block(chunks, tips)
    max_cite = len(chunks) + len(tips)

    data = llm.json(
        [
            {"role": "system", "content": prompts.SYSTEM_PERSONA},
            {"role": "user", "content": prompts.QA_PROMPT.format(evidence=evidence, question=question)},
        ],
        temperature=0.2,
        max_tokens=800,
    )
    ans = (data.get("answer") or "").strip()
    if len(ans) < 4:  # 模型偶发只返回引用标记，重试一次
        retry = llm.json(
            [
                {"role": "system", "content": prompts.SYSTEM_PERSONA},
                {"role": "user", "content": prompts.QA_PROMPT.format(evidence=evidence, question=question)},
            ],
            temperature=0.4,
            max_tokens=800,
        )
        ans = (retry.get("answer") or "").strip() or "这个问题我需要再确认一下，建议问一下药师。"
    verdict = verify(question, ans, evidence, max_cite)
    final = verdict.get("final_answer") or ans

    cite_ids = {int(c) for c in re.findall(r"\[(\d+)\]", final) if 1 <= int(c) <= max_cite}
    for u in data.get("used") or []:
        try:
            u = int(u)
        except (TypeError, ValueError):
            continue
        if 1 <= u <= max_cite:
            cite_ids.add(u)
    if not cite_ids and not data.get("refused"):
        # 模型漏标引用时兜底：至少挂上召回的最高分证据，保证「可溯源」
        cite_ids.add(1)
    cites = sorted(cite_ids)
    if cites and not re.search(r"\[\d+\]", final) and not data.get("refused"):
        final += "（来源：" + "".join(f"[{c}]" for c in cites) + "）"

    mapping = []
    for i, c in enumerate(chunks, start=1):
        if i in cites:
            mapping.append({"id": i, "text": c.text, "section": c.section})
    for j, t in enumerate(tips, start=len(chunks) + 1):
        if j in cites:
            mapping.append({"id": j, "text": f"{t['title']}：{t['text']}", "section": "elderly_tip"})

    return {
        "answer": final,
        "raw_answer": ans,
        "refused": bool(data.get("refused")),
        "need_doctor": bool(data.get("need_doctor")) or bool(verdict.get("model", {}).get("risk_advice")),
        "citations": mapping,
        "evidence": [{"id": i, "text": c.text, "section": c.section} for i, c in enumerate(chunks, start=1)],
        "guard": verdict,
        "disclaimer": config.DISCLAIMER,
    }


# --------------------------------------------------- 4. 多药同服冲突分析
def analyze_interactions(labels: list[dict]) -> dict:
    names = [l.get("drug_name", "") for l in labels if l.get("drug_name")]
    kb_hits = Retriever.kb_lookup(names)
    material = []
    for l in labels:
        material.append(
            f"### {l['drug_name']}（{l.get('spec','')}）\n"
            f"用法用量：{'; '.join(l.get('dosage') or []) or '未写明'}\n"
            f"禁忌：{'; '.join(l.get('contraindications') or []) or '未写明'}\n"
            f"相互作用：{'; '.join(l.get('interactions') or []) or '未写明'}\n"
            f"注意事项：{'; '.join(l.get('precautions') or []) or '未写明'}"
        )
    kb_text = "\n".join(
        f"[{e['id']}] {e['a']} + {e['b']}（{e['level']}）：{e['mechanism']} 后果：{e['consequence']} 处置：{e['advice']}"
        for e in kb_hits
    ) or "（知识库未命中）"

    data = llm.json(
        [
            {"role": "system", "content": prompts.SYSTEM_PERSONA},
            {"role": "user", "content": prompts.INTERACTION_PROMPT.format(drugs="\n\n".join(material), kb_hits=kb_text)},
        ],
        temperature=0.1,
        max_tokens=1600,
    )
    data["kb_hits"] = kb_hits
    data["disclaimer"] = config.DISCLAIMER
    return data


# ------------------------------------------------------------ 5. 家属摘要
def family_summary(labels: list[dict], extra: str = "") -> dict:
    materials = []
    for l in labels:
        materials.append(
            f"{l['drug_name']}（{l.get('spec','')}）：用法 {'; '.join(l.get('dosage') or [])}；"
            f"禁忌 {'; '.join(l.get('contraindications') or []) or '未写明'}"
        )
    data = llm.json(
        [
            {"role": "system", "content": prompts.SYSTEM_PERSONA},
            {"role": "user", "content": prompts.FAMILY_PROMPT.format(materials="\n".join(materials) + "\n" + extra)},
        ],
        temperature=0.3,
        max_tokens=1200,
    )
    data["disclaimer"] = config.DISCLAIMER
    return data


# ------------------------------------------------------- 6. Function Calling
def _exec_tool(name: str, args: dict, label: dict, state: dict) -> Any:
    if name == "search_label":
        r = Retriever(label)
        chunks = r.retrieve(args.get("query", ""), top_k=int(args.get("top_k") or 4))
        return [{"cid": c.cid, "section": c.section, "text": c.text} for c in chunks]
    if name == "check_interaction":
        hits = Retriever.kb_lookup([args.get("drug_a", ""), args.get("drug_b", "")])
        if not hits:
            return {"found": False, "message": "知识库未收录该组合，建议药师人工核对"}
        return {"found": True, "entries": hits}
    if name == "get_elderly_tip":
        return Retriever.elderly_tips(args.get("topic", ""), top_k=2)
    if name == "set_med_reminder":
        plan = {"drug": args.get("drug"), "times": args.get("times") or [], "note": args.get("note", "")}
        state.setdefault("reminders", []).append(plan)
        return {"ok": True, "saved": plan}
    if name == "escalate_to_human":
        state["escalated"] = args.get("reason", "")
        return {"ok": True, "ticket": new_id("tk"), "message": "已为您登记，药师会在 2 小时内回电（演示）"}
    return {"error": f"unknown tool {name}"}


def run_agent(label: dict, question: str, max_rounds: int = 5) -> dict:
    """多轮 Function Calling：模型决定调什么工具，工具结果回灌，直到给出答案。"""
    messages: list[dict] = [
        {"role": "system", "content": prompts.SYSTEM_PERSONA
         + "\n你可以调用工具。规则："
           "1) 凡是涉及用法用量、禁忌、副作用、与其他药同服的问题，必须先调用 search_label 或 check_interaction 取得证据，再回答。"
           "2) 引用格式为 [n]，n 是「第几次工具调用」的序号（第一次调用是 [1]，第二次是 [2]），不要使用工具返回结果里的 cid 字段。"
           "3) 证据不足时调用 escalate_to_human。"
           "4) 用户要求设提醒时调用 set_med_reminder。"},
        {"role": "user", "content": f"当前药品：{label['drug_name']}。用户问题：{question}"},
    ]
    state: dict = {"reminders": []}
    trace: list[dict] = []
    final_text = ""

    for rnd in range(max_rounds):
        msg = llm.chat(messages, tools=TOOLS, tool_choice="auto", temperature=0.2, max_tokens=900)
        calls = msg.get("tool_calls") or []
        if msg.get("content"):
            final_text = msg["content"]
        if not calls:
            trace.append({"round": rnd + 1, "type": "final", "content": final_text})
            break
        messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
        for call in calls:
            fn = call["function"]["name"]
            try:
                args = json.loads(call["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            t0 = time.time()
            result = _exec_tool(fn, args, label, state)
            ms = int((time.time() - t0) * 1000)
            trace.append({"round": rnd + 1, "type": "tool", "tool": fn, "args": args, "result": result, "ms": ms})
            messages.append({
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "content": json.dumps(result, ensure_ascii=False)[:4000],
            })
    else:
        trace.append({"round": max_rounds, "type": "max_rounds"})

    # 最终答案再过一道护栏
    if len(final_text.strip()) < 4:
        final_text = "这个问题我需要再确认一下，建议带着药盒问一下药师或医生。"
    evidence = "\n".join(
        f"[{i+1}] {json.dumps(t['result'], ensure_ascii=False)[:300]}"
        for i, t in enumerate([x for x in trace if x["type"] == "tool"])
    ) or (final_text or "")
    verdict = verify(question, final_text, evidence, max(1, len([x for x in trace if x["type"] == "tool"])))
    return {
        "answer": verdict.get("final_answer") or final_text,
        "trace": trace,
        "reminders": state.get("reminders", []),
        "escalated": state.get("escalated", ""),
        "guard": verdict,
        "disclaimer": config.DISCLAIMER,
    }
