"""由 build_report.py 的内容块生成 HTML，再交给 Edge 无头打印成 PDF。

之所以不直接用 Word 转 PDF：本机 Word COM 在长文档 + 高清图的情况下会挂起，
而 Edge 的 print-to-pdf 稳定、可重复，且排版完全由 CSS 控制。

用法：python docs/build_report_pdf.py
输出：docs/out/安心药声-AI技术实现报告.pdf
"""
from __future__ import annotations

import html
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "docs"))

import build_report as br  # noqa: E402

OUT = ROOT / "docs" / "out"
OUT.mkdir(parents=True, exist_ok=True)
BLOCKS: list[dict] = []

TEAL_HEX = "0F7A68"
MUTED_HEX = "6B8079"


def _hex(color) -> str:
    try:
        return str(color)
    except Exception:
        return TEAL_HEX


def patch() -> None:
    def wrap(name: str, kind: str, text_arg: int = 1, extra: int | None = None):
        orig = getattr(br, name)

        def fn(*a, **k):
            r = orig(*a, **k)
            rec = {"t": kind, "text": a[text_arg] if len(a) > text_arg else k.get("text", "")}
            if extra is not None and len(a) > extra:
                rec["extra"] = a[extra]
            elif extra is not None:
                rec["extra"] = k.get("num") or k.get("caption")
            if kind == "p":
                rec["bold"] = bool(k.get("bold"))
                rec["indent"] = k.get("indent", True)
                rec["color"] = _hex(k.get("color")) if k.get("color") else "10241F"
            if kind == "code":
                rec["caption"] = (a[2] if len(a) > 2 else k.get("caption")) or ""
            if kind == "figure":
                rec["img"] = str(a[1]) if len(a) > 1 else ""
                rec["caption"] = a[2] if len(a) > 2 else ""
            if kind == "table":
                rec["header"] = [str(x) for x in a[1]]
                rec["rows"] = [[str(c) for c in row] for row in a[2]]
                rec["font"] = a[4] if len(a) > 4 else k.get("font", 8.5)
            BLOCKS.append(rec)
            return r

        setattr(br, name, fn)

    wrap("h1", "h1", 1, 2)
    wrap("h2", "h2")
    wrap("para", "p")
    wrap("bullet", "li")
    wrap("code_block", "code")
    wrap("figure", "figure")
    wrap("table", "table")
    wrap("callout", "callout")


def block_html(b: dict) -> str:
    t = b["t"]
    if t == "h1":
        num = b.get("extra") or ""
        # 摘要与第一章连排，避免首页大片留白
        cls = "sec nobreak" if b["text"] in ("摘要",) or "项目背景" in b["text"] else "sec"
        return f'<h1 class="{cls}"><span class="num">{html.escape(str(num))}</span>{html.escape(b["text"])}</h1>'
    if t == "h2":
        return f'<h2>{html.escape(b["text"])}</h2>'
    if t == "p":
        cls = " class=\"muted\"" if b.get("color") == MUTED_HEX else ""
        style = " style=\"font-weight:700\"" if b.get("bold") else ""
        return f"<p{cls}{style}>{html.escape(b['text'])}</p>"
    if t == "li":
        return f"<li>{html.escape(b['text'])}</li>"
    if t == "code":
        cap = f'<div class="cap">{html.escape(b.get("caption") or "")}</div>' if b.get("caption") else ""
        return f'<pre>{html.escape(b["text"])}</pre>{cap}'
    if t == "callout":
        return f'<div class="callout">{html.escape(b["text"])}</div>'
    if t == "figure":
        p = Path(b.get("img", ""))
        if not p.exists():
            return ""
        return (f'<figure><img src="{p.as_uri()}"><figcaption>{html.escape(b.get("caption") or "")}</figcaption></figure>')
    if t == "table":
        head = "".join(f"<th>{html.escape(h)}</th>" for h in b["header"])
        body = "".join(
            "<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in row) + "</tr>" for row in b["rows"]
        )
        fs = b.get("font", 8.5)
        return f'<table style="font-size:{fs}pt"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
    return ""


CSS = """
@page { size: A4; margin: 20mm 18mm 18mm 18mm; }
* { box-sizing: border-box; }
body { font-family: "Microsoft YaHei","PingFang SC",sans-serif; font-size: 10.5pt; color:#10241F;
       line-height: 1.7; margin:0; }
h1.sec { font-size: 17pt; margin: 0 0 10px; padding-bottom: 6px; border-bottom: 2px solid #0F7A68;
         page-break-before: always; color:#10241F; }
h1.sec.nobreak { page-break-before: avoid; margin-top: 22px; }
h1.sec .num { color:#0F7A68; margin-right: 8px; }
h2 { font-size: 12.5pt; color:#0F7A68; margin: 16px 0 6px; page-break-after: avoid; }
p { margin: 0 0 8px; text-indent: 2em; text-align: justify; }
p.muted { color:#6B8079; }
ul { margin: 0 0 10px; padding-left: 22px; }
li { margin: 3px 0; }
pre { background:#F3F7F5; border-left: 3px solid #0F7A68; padding: 10px 12px; margin: 6px 0 4px;
      font-family: Consolas, monospace; font-size: 8.6pt; line-height: 1.45; white-space: pre-wrap;
      word-break: break-word; page-break-inside: avoid; }
.cap { color:#6B8079; font-size: 8.5pt; margin: 2px 0 12px; }
.callout { background:#E6F6F1; color:#0F7A68; font-weight:700; padding: 10px 14px; margin: 10px 0 14px;
           font-size: 9.5pt; border-radius: 4px; }
figure { margin: 8px 0 14px; text-align:center; page-break-inside: avoid; }
figure img { max-width: 100%; border: 1px solid #E1EAE6; border-radius: 4px; }
figcaption { color:#6B8079; font-size: 8.5pt; margin-top: 5px; }
table { width:100%; border-collapse: collapse; margin: 6px 0 14px; page-break-inside: avoid; }
th { background:#0F7A68; color:#fff; font-weight:700; padding: 5px 7px; text-align:left; border:1px solid #0F7A68; }
td { padding: 4px 7px; border: 1px solid #DDE8E3; vertical-align: top; line-height: 1.45; }
tbody tr:nth-child(even) { background: #F7FAF8; }
.cover { height: 245mm; display:flex; flex-direction:column; justify-content:center; text-align:center;
         page-break-after: always; }
.cover .k { font-size: 40pt; font-weight:800; color:#0F7A68; letter-spacing: 4px; }
.cover .s { font-size: 22pt; font-weight:700; color:#10241F; margin-top: 8px; }
.cover .d { font-size: 11pt; color:#6B8079; margin-top: 18px; line-height: 1.9; }
.cover .m { font-size: 9.5pt; color:#8FA9A1; margin-top: 70px; line-height: 2.1; }
"""


def render() -> Path:
    body = "".join(block_html(b) for b in BLOCKS)
    cover = """
    <div class="cover">
      <div class="k">安心药声</div>
      <div class="s">AI 技术实现报告</div>
      <div class="d">药品说明书多模态解析 · 可溯源用药问答 · 多药冲突 Agent</div>
      <div class="m">
        郭翰林　·　学号 2025413087<br>
        文档版本：v1.0<br>
        技术栈：Python 3.13 / FastAPI / 原生前端 / OpenAI-Compatible 大模型<br>
        开源仓库：github.com/code-muncher-ghl/anxin-yaosheng<br>
        编制日期：2026 年 11 月
      </div>
    </div>
    """
    doc = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
    <title>安心药声 · AI 技术实现报告</title><style>{CSS}</style></head>
    <body>{cover}{body}</body></html>"""
    hp = OUT / "report.html"
    hp.write_text(doc, encoding="utf-8")
    return hp


def to_pdf(html_path: Path) -> Path:
    edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    pdf = OUT / "安心药声-AI技术实现报告.pdf"
    if pdf.exists():
        pdf.unlink()
    subprocess.run(
        [str(edge), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf}", html_path.as_uri()],
        check=False, capture_output=True, timeout=180,
    )
    for _ in range(30):
        if pdf.exists() and pdf.stat().st_size > 20_000:
            break
        time.sleep(1)
    return pdf


def main() -> None:
    patch()
    br.build()
    print("blocks:", len(BLOCKS))
    hp = render()
    print("html:", hp)
    pdf = to_pdf(hp)
    print("pdf:", pdf, f"{pdf.stat().st_size/1024:.0f} KB" if pdf.exists() else "FAILED")


if __name__ == "__main__":
    main()

