"""把源码渲染成「代码截图」PNG，用于技术报告与 BP。

用法：python tools/render_code.py
输出：assets/shots/code_*.png
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "shots"
OUT.mkdir(parents=True, exist_ok=True)

KEYWORDS = [
    "def", "class", "return", "if", "else", "elif", "for", "in", "while", "import", "from",
    "try", "except", "finally", "with", "as", "and", "or", "not", "None", "True", "False",
    "raise", "lambda", "yield", "async", "await", "pass", "break", "continue", "global",
]
KW_RE = re.compile(r"\b(" + "|".join(KEYWORDS) + r")\b")
TOKEN_RE = re.compile(r"(#.*$)|(\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*')")

# (输出名, 文件, 起始锚点, 行数, 标题)
SNIPPETS = [
    ("code_llm", "app/llm.py", "def _post", 34, "llm.py · OpenAI-Compatible 统一调用层（限流 / 重试 / 用量统计）"),
    ("code_prompt", "app/prompts.py", "PARSE_PROMPT = ", 30, "prompts.py · 说明书解析：强制 evidence 锚点，禁止知识补全"),
    ("code_guard", "app/guard.py", "def check_numbers", 24, "guard.py · 数字接地：回答中的数字必须命中证据原文"),
    ("code_agent", "app/agent.py", "def run_agent", 40, "agent.py · Function Calling 主循环：模型决定调什么工具"),
    ("code_rag", "app/rag.py", "def retrieve", 32, "rag.py · 混合检索：BM25 + 章节意图先验"),
]


def highlight(line: str) -> str:
    """先在原始文本上切分注释/字符串，再分别转义，避免把 <span> 当成字符串处理。"""
    out, pos = [], 0
    for m in TOKEN_RE.finditer(line):
        code = line[pos:m.start()]
        out.append(_code(code))
        if m.group(1):
            out.append(f'<span class="c">{html.escape(m.group(1))}</span>')
        else:
            out.append(f'<span class="s">{html.escape(m.group(2))}</span>')
        pos = m.end()
    out.append(_code(line[pos:]))
    return "".join(out)


def _code(text: str) -> str:
    if not text:
        return ""
    esc = html.escape(text)
    esc = KW_RE.sub(r'<span class="k">\1</span>', esc)
    esc = re.sub(r"(^\s*)(@\w+)", r'\1<span class="d">\2</span>', esc)
    return esc


def build_html(path: Path, anchor: str, count: int, title: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith(anchor)), 0) + 1
    body = []
    for i in range(start - 1, min(start - 1 + count, len(lines))):
        body.append(
            f'<div class="ln"><span class="no">{i+1:>4}</span>'
            f'<span class="code">{highlight(lines[i]) or "&nbsp;"}</span></div>'
        )
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ background:#0d1f1b; padding:30px 36px; font-family:Consolas,"JetBrains Mono",monospace; width:1200px; }}
    .bar {{ display:flex; gap:8px; align-items:center; margin-bottom:16px; }}
    .dot {{ width:11px; height:11px; border-radius:50%; }}
    .title {{ color:#7fb0a4; font-size:13px; margin-left:10px; font-family:"Microsoft YaHei"; }}
    .ln {{ display:flex; font-size:14.5px; line-height:1.62; }}
    .no {{ color:#3f5f57; width:44px; text-align:right; padding-right:16px; user-select:none; flex:0 0 auto; }}
    .code {{ color:#cfe8e0; white-space:pre-wrap; word-break:break-word; }}
    .k {{ color:#7ee0c0; font-weight:600; }} .s {{ color:#f0c987; }}
    .c {{ color:#5b7f76; font-style:italic; }} .d {{ color:#9fc6ff; }}
    </style></head><body>
    <div class="bar"><span class="dot" style="background:#ff5f57"></span><span class="dot" style="background:#febc2e"></span>
    <span class="dot" style="background:#28c840"></span><span class="title">{html.escape(title)}</span></div>
    {''.join(body)}
    </body></html>"""


def main() -> None:
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="msedge")
        except Exception:
            browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 400}, device_scale_factor=2)
        for name, rel, anchor, count, title in SNIPPETS:
            page.set_content(build_html(ROOT / rel, anchor, count, title))
            page.wait_for_timeout(150)
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
            print("saved", name)
        browser.close()


if __name__ == "__main__":
    main()
