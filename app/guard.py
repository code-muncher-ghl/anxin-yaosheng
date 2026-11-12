"""安全护栏层 —— 本项目「不是套壳」的关键证据之一。

四道闸门：
1. 数字接地（Number Grounding）：回答里每个数字必须在证据原文中出现过；
2. 引用校验（Citation Check）：回答里的 [n] 必须落在证据编号范围内；
3. 危险建议拦截（Risk Guard）：停药/换药/加量/诊断类表述强制改写为「请医生判断」；
4. 独立复核（Verifier）：另起一次模型调用逐句核对，不通过则回退到保守答案。
"""
from __future__ import annotations

import re

from . import config, prompts
from .llm import llm

NUM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(mg|毫克|g|克|ml|毫升|片|粒|袋|支|滴|次|天|日|周|小时|分钟|%|单位|iu|ug|微克)", re.I)
CITE_RE = re.compile(r"\[(\d+)\]")
RISK_PATTERNS = [
    (re.compile(r"(可以|建议|不妨|直接)(停药|停掉|停用|换药|换一种|加量|减量|加倍|停药观察)"), "调整用药"),
    (re.compile(r"(您|你)(就是|应该是|肯定是)(得了|患了|属于)"), "下诊断"),
    (re.compile(r"(这个药|本品)(能|可以)(治好|治愈|根治)"), "承诺疗效"),
]


def normalize_number(m: str) -> str:
    return m.lower().replace("毫克", "mg").replace("毫升", "ml").replace("微克", "ug")


def extract_numbers(text: str) -> set[str]:
    return {normalize_number(f"{n}{u}") for n, u in NUM_RE.findall(text or "")}


def check_numbers(answer: str, evidence_text: str) -> list[str]:
    """返回回答里「证据中找不到」的数字，理想情况为空。"""
    ev = extract_numbers(evidence_text)
    ev_nums = {n for n in ev}
    # 证据里没带单位的裸数字也纳入（如「一日1次」被抽成 1次）
    ev_raw = set(re.findall(r"\d+(?:\.\d+)?", evidence_text or ""))
    bad = []
    for num in extract_numbers(answer):
        digits = re.match(r"(\d+(?:\.\d+)?)", num).group(1)
        if num in ev_nums or digits in ev_raw:
            continue
        bad.append(num)
    return bad


def check_citations(answer: str, max_cite: int) -> list[int]:
    return sorted({int(c) for c in CITE_RE.findall(answer or "") if not (1 <= int(c) <= max_cite)})


CONSULT_HINTS = ("是否", "能不能", "可不可以", "该不该", "咨询", "问一下", "问医生", "听医生", "由医生")


def risk_scan(text: str) -> list[str]:
    """识别「越界行医」表述；「是否/能不能/咨询医生」这类把决定权交回医生的句子不算。"""
    hits = []
    for pattern, label in RISK_PATTERNS:
        for m in pattern.finditer(text or ""):
            window = (text[max(0, m.start() - 10): m.start()] + m.group(0))
            if any(h in window for h in CONSULT_HINTS):
                continue
            hits.append(label)
            break
    return hits


def harden(answer: str, bad_numbers: list[str], risks: list[str], need_doctor: bool) -> str:
    """不通过时的保守化改写：不删除信息，只把「断言」降级为「建议核实」。"""
    out = answer
    if bad_numbers:
        out += "\n\n（提示：上面有些数字说明书原文里没有明确写出，我已经把它们标出来，请以药盒和说明书为准。）"
    if risks:
        out += "\n\n（这句话涉及调整用药，需要医生当面判断，我不能替您决定。）"
        need_doctor = True
    if need_doctor and "医生" not in out:
        out += "\n\n建议带着药盒去医院或药店咨询医生、药师。"
    return out


def verify(question: str, answer: str, evidence_text: str, max_cite: int) -> dict:
    """规则闸门 + 模型复核，双保险。"""
    rule_bad_numbers = check_numbers(answer, evidence_text)
    rule_bad_cites = check_citations(answer, max_cite)
    rule_risks = risk_scan(answer)

    verdict = {
        "pass": True,
        "rule": {
            "unsupported_numbers": rule_bad_numbers,
            "invalid_citations": rule_bad_cites,
            "risk_advice": bool(rule_risks),
        },
        "model": {},
    }
    if rule_bad_numbers or rule_bad_cites or rule_risks:
        verdict["pass"] = False
        verdict["final_answer"] = harden(answer, rule_bad_numbers, rule_risks, bool(rule_risks))
        return verdict

    try:
        m = llm.json(
            [
                {"role": "system", "content": prompts.SYSTEM_PERSONA},
                {"role": "user", "content": prompts.VERIFY_PROMPT.format(evidence=evidence_text, answer=answer)},
            ],
            model=config.LLM_VERIFY_MODEL,
            temperature=0.0,
            max_tokens=600,
        )
    except Exception as exc:  # 复核失败不阻断主流程，但降级为「需人工确认」
        verdict["model"] = {"error": str(exc)}
        return verdict

    verdict["model"] = m
    # 复核员只有在「能明确指出问题」时才否决；只说 pass=false 却不给理由的一律视为通过，
    # 避免弱模型把正确答案误杀成「说明书没写」。
    has_evidence_of_problem = bool(
        m.get("unsupported_numbers") or m.get("unsupported_claims") or m.get("invalid_citations")
    )
    if (not m.get("pass", True) or m.get("risk_advice")) and (
        has_evidence_of_problem or m.get("risk_advice")
    ):
        verdict["pass"] = False
        verdict["final_answer"] = m.get("fixed_answer") or harden(
            answer,
            m.get("unsupported_numbers") or [],
            ["模型复核未通过"] if m.get("risk_advice") else [],
            True,
        )
    else:
        verdict["final_answer"] = answer
    return verdict
