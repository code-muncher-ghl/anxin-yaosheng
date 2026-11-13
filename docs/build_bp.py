"""生成《安心药声 · 商业计划书》PPTX（16:9，20 页）

用法：python docs/build_bp.py
输出：docs/out/安心药声-商业计划书.pptx
"""
from __future__ import annotations

import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "out"
OUT.mkdir(parents=True, exist_ok=True)
SHOTS = ROOT / "assets" / "shots"

INK = RGBColor(0x10, 0x24, 0x1F)
INK2 = RGBColor(0x3D, 0x55, 0x4E)
MUTED = RGBColor(0x6B, 0x80, 0x79)
FAINT = RGBColor(0x8F, 0xA9, 0xA1)
TEAL = RGBColor(0x0F, 0x7A, 0x68)
TEAL2 = RGBColor(0x14, 0xA0, 0x85)
TEAL_SOFT = RGBColor(0xE6, 0xF6, 0xF1)
AMBER = RGBColor(0xD9, 0x84, 0x28)
AMBER_SOFT = RGBColor(0xFD, 0xF1, 0xE2)
RED = RGBColor(0xC8, 0x39, 0x2F)
RED_SOFT = RGBColor(0xFD, 0xEC, 0xEA)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BG = RGBColor(0xF7, 0xFA, 0xF8)
LINE = RGBColor(0xE1, 0xEA, 0xE6)
DARK = RGBColor(0x0B, 0x2A, 0x24)

FONT = "微软雅黑"
W, H = Inches(13.333), Inches(7.5)
TOTAL = 20


def new_deck() -> Presentation:
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    return prs


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def rect(slide, x, y, w, h, fill=None, line=None, radius=None, transparency=None):
    st = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    sp = slide.shapes.add_shape(st, int(x), int(y), int(w), int(h))
    if radius:
        try:
            sp.adjustments[0] = radius
        except Exception:
            pass
    if fill is None:
        sp.fill.background()
    else:
        sp.fill.solid()
        sp.fill.fore_color.rgb = fill
    if line is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line
        sp.line.width = Pt(1)
    sp.shadow.inherit = False
    if sp.has_text_frame:
        sp.text_frame.word_wrap = True
    return sp


def text(slide, x, y, w, h, content, size=18, color=INK, bold=False,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.3, font=FONT):
    tb = slide.shapes.add_textbox(int(x), int(y), int(w), int(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    lines = content.split("\n") if isinstance(content, str) else content
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = font
    return tb


def bg(slide, color=BG):
    rect(slide, 0, 0, W, H, color)


def page_title(slide, kicker, title, sub=None):
    text(slide, Inches(0.72), Inches(0.42), Inches(4), Inches(0.3), kicker, 10.5, TEAL, True)
    text(slide, Inches(0.72), Inches(0.7), Inches(11.9), Inches(0.62), title, 28, INK, True)
    if sub:
        text(slide, Inches(0.72), Inches(1.32), Inches(11.9), Inches(0.42), sub, 12.5, MUTED, spacing=1.4)
    rect(slide, Inches(0.72), Inches(1.74), Inches(0.6), Inches(0.045), TEAL)


def footer(slide, n):
    text(slide, Inches(0.72), Inches(7.04), Inches(7), Inches(0.26),
         "安心药声 · 拍一下说明书，听见安全用药", 8.5, FAINT)
    text(slide, Inches(11.6), Inches(7.04), Inches(1.0), Inches(0.26), f"{n:02d} / {TOTAL}", 8.5, FAINT, align=PP_ALIGN.RIGHT)


def stat_card(slide, x, y, w, h, number, label, source="", color=TEAL, bgc=WHITE):
    rect(slide, x, y, w, h, bgc, LINE, radius=0.08)
    text(slide, x + Inches(0.24), y + Inches(0.18), w - Inches(0.45), Inches(0.52), number, 30, color, True)
    text(slide, x + Inches(0.24), y + Inches(0.72), w - Inches(0.45), Inches(0.42), label, 10.5, INK2, spacing=1.35)
    if source:
        text(slide, x + Inches(0.24), y + h - Inches(0.34), w - Inches(0.45), Inches(0.24), source, 7.5, FAINT)


def card(slide, x, y, w, h, title, body, accent=TEAL, bgc=WHITE, title_size=13, body_size=10.5):
    rect(slide, x, y, w, h, bgc, LINE, radius=0.06)
    rect(slide, x, y, Inches(0.055), h, accent)
    text(slide, x + Inches(0.26), y + Inches(0.18), w - Inches(0.4), Inches(0.3), title, title_size, accent, True)
    text(slide, x + Inches(0.26), y + Inches(0.56), w - Inches(0.42), h - Inches(0.7), body, body_size, INK2, spacing=1.5)


# ------------------------------------------------------------------ 01 封面
def s01_cover(prs):
    s = blank(prs)
    rect(s, 0, 0, W, H, DARK)
    rect(s, Inches(8.1), Inches(-1.6), Inches(7.2), Inches(7.2), RGBColor(0x12, 0x46, 0x3B), radius=0.5)
    rect(s, Inches(-1.8), Inches(4.5), Inches(6.4), Inches(5.2), RGBColor(0x0D, 0x33, 0x2B), radius=0.5)
    rect(s, Inches(9.4), Inches(3.9), Inches(2.6), Inches(2.6), RGBColor(0x17, 0x55, 0x47), radius=0.5)

    text(s, Inches(0.92), Inches(0.95), Inches(7), Inches(0.28),
         "第十届中国国际「互联网+」大学生创新创业大赛 · 高教主赛道", 10, RGBColor(0x8F, 0xB5, 0xAA))
    text(s, Inches(0.92), Inches(1.28), Inches(4), Inches(0.28), "公益组 · 银发经济", 9.5, RGBColor(0x6F, 0x95, 0x8B))

    text(s, Inches(0.92), Inches(2.05), Inches(7.2), Inches(1.0), "安心药声", 58, WHITE, True)
    text(s, Inches(0.92), Inches(3.12), Inches(7.2), Inches(0.55), "拍一下说明书，听见安全用药", 24, RGBColor(0x8F, 0xE0, 0xC9), True)
    text(s, Inches(0.92), Inches(3.86), Inches(6.4), Inches(0.9),
         "面向 60 岁以上老人及其子女的\n药品说明书 AI 语音解读与多药冲突预警助手", 13.5, RGBColor(0xBF, 0xD8, 0xD1), spacing=1.55)

    tags = [("多模态识别", 1.28), ("可溯源 RAG", 1.42), ("Function Calling", 1.72), ("幻觉四道闸门", 1.52)]
    x = Inches(0.92)
    for t, tw in tags:
        w = Inches(tw)
        rect(s, x, Inches(5.16), w, Inches(0.34), None, RGBColor(0x3E, 0x7A, 0x6C), radius=0.5)
        text(s, x, Inches(5.21), w, Inches(0.26), t, 9, RGBColor(0xB8, 0xDE, 0xD3), align=PP_ALIGN.CENTER)
        x += w + Inches(0.1)

    text(s, Inches(0.92), Inches(6.36), Inches(6), Inches(0.26), "参赛团队：郭翰林 · 计算机科学与技术", 9.5, RGBColor(0x8F, 0xA9, 0xA1))
    text(s, Inches(0.92), Inches(6.66), Inches(6), Inches(0.26), "2026 年 11 月", 9.5, RGBColor(0x6F, 0x8B, 0x83))
    return s


# ------------------------------------------------------------- 02 用户画像
def s02_persona(prs, n):
    s = blank(prs)
    bg(s)
    page_title(s, "用户洞察", "三个真实的人，三种说不出口的难",
               "基于 12 位 60+ 老人、9 位异地子女、2 位执业药师的访谈")
    data = [
        ("王阿姨 · 68 岁", "独居 · 高血压 / 高血脂 / 骨质疏松\n每天 5 种药", [
            "「这字太小了，得拿放大镜，还得对着灯」",
            "孩子忙，不好意思总打电话问",
            "吃药全凭记忆，常忘记吃没吃",
        ], TEAL),
        ("李叔 · 74 岁", "糖尿病 12 年 · 白内障术后视力差\n同时吃 7 种药，跨 3 个科室", [
            "只认药盒颜色，不认药名",
            "从没人帮他核对过药会不会打架",
            "感冒自己加抗生素，不知道危险",
        ], AMBER),
        ("小陈 · 32 岁", "在一线城市工作 · 父母在老家\n每周电话必问「药吃了没」", [
            "看不见说明书，无法判断父母说得对不对",
            "想说点什么，又怕显得不信任",
            "只想要一份能直接看懂的用药清单",
        ], RGBColor(0x39, 0x5A, 0x52)),
    ]
    for i, (name, meta, pains, accent) in enumerate(data):
        y = Inches(1.98) + Inches(1.62) * i
        rect(s, Inches(0.72), y, Inches(11.9), Inches(1.44), WHITE, LINE, radius=0.05)
        rect(s, Inches(0.72), y, Inches(0.07), Inches(1.44), accent)
        text(s, Inches(1.02), y + Inches(0.16), Inches(2.7), Inches(0.28), name, 12.5, INK, True)
        text(s, Inches(1.02), y + Inches(0.5), Inches(2.7), Inches(0.7), meta, 8.5, MUTED, spacing=1.45)
        for j, p in enumerate(pains):
            text(s, Inches(3.95), y + Inches(0.18) + Inches(0.36) * j, Inches(8.4), Inches(0.3), "· " + p, 10, INK2)
    text(s, Inches(0.72), Inches(6.82), Inches(11.9), Inches(0.26),
         "关键洞察：老人是使用者，子女是付费者，药店是渠道 —— 三者不是同一群人。", 9.5, TEAL, True)
    footer(s, n)


# ---------------------------------------------------------- 03 痛点一 字号
def s03_pain_vision(prs, n):
    s = blank(prs)
    bg(s)
    page_title(s, "痛点一 · 看不见", "说明书的字，本来就不是写给老人看的",
               "记者抽测 10 种常用药：8 种字号小于 5 号字，部分抗生素用 6 号字，一粒米可盖住 4~6 个字")
    stat_card(s, Inches(0.72), Inches(1.98), Inches(3.8), Inches(1.5), "8 / 10",
              "抽测药品字号小于 5 号字", "中央广电总台中国之声 2025-12")
    stat_card(s, Inches(4.75), Inches(1.98), Inches(3.8), Inches(1.5), "96.8%",
              "受访者认为说明书字号太小", "纵览新闻 359 份问卷 2025-03")
    stat_card(s, Inches(8.78), Inches(1.98), Inches(3.84), Inches(1.5), "1765 个",
              "全国参加说明书适老化试点的品种", "中国医药报 2025-08")

    rect(s, Inches(0.72), Inches(3.75), Inches(11.9), Inches(2.55), WHITE, LINE, radius=0.05)
    text(s, Inches(1.02), Inches(3.94), Inches(4), Inches(0.28), "我们看到的真实场景", 10.5, TEAL, True)
    quotes = [
        "「这字太小了，我得拿放大镜，还得对着灯。」—— 王阿姨，68 岁",
        "「上面写的‘慎用’‘禁用’，我也分不清哪个更严重。」—— 李叔，74 岁",
        "「我妈打电话问我，我在外地也看不见说明书啊。」—— 小陈，32 岁",
    ]
    for i, q in enumerate(quotes):
        text(s, Inches(1.02), Inches(4.36) + Inches(0.5) * i, Inches(11.2), Inches(0.34), q, 11, INK2)
    rect(s, Inches(1.02), Inches(5.72), Inches(11.3), Inches(0.02), LINE)
    text(s, Inches(1.02), Inches(5.84), Inches(11.3), Inches(0.32),
         "→ 结论：不是「老年人不爱学习新东西」，是产品根本没给他们留入口。", 10.5, TEAL, True)
    footer(s, n)


# ------------------------------------------------------- 04 痛点二 多重用药
def s04_pain_mix(prs, n):
    s = blank(prs)
    bg(s)
    page_title(s, "痛点二 · 会打架", "老人吃的不是一种药，是一把药",
               "多重用药是老年医学公认的风险源，而「药与药之间」恰恰是说明书最难读的部分")
    stats = [
        ("48%", "中国老年患者多重用药合并患病率\n（住院人群高达 73%）", "Front Pharmacol 2022 · meta 分析", TEAL),
        ("39%", "存在潜在不适当用药（PIM）\n即「本来不该吃这个药」", "Front Pharmacol 2022", AMBER),
        ("272.8 万份", "2025 年全国药品不良反应报告", "国家药品不良反应监测中心", TEAL),
        ("35.0%", "其中 65 岁及以上占比，为各年龄组最高\n约合 95 万份/年", "同上", RED),
    ]
    for i, (num, label, src, c) in enumerate(stats):
        col, row = i % 2, i // 2
        x = Inches(0.72) + Inches(6.12) * col
        y = Inches(1.98) + Inches(1.52) * row
        rect(s, x, y, Inches(5.78), Inches(1.34), WHITE, LINE, radius=0.06)
        text(s, x + Inches(0.28), y + Inches(0.18), Inches(2.6), Inches(0.45), num, 24, c, True)
        text(s, x + Inches(0.28), y + Inches(0.68), Inches(5.2), Inches(0.45), label, 9.5, INK2, spacing=1.35)
        text(s, x + Inches(0.28), y + Inches(1.06), Inches(5.2), Inches(0.22), src, 7.5, FAINT)

    rect(s, Inches(0.72), Inches(5.16), Inches(11.9), Inches(1.15), AMBER_SOFT, None, radius=0.08)
    text(s, Inches(1.0), Inches(5.32), Inches(11.3), Inches(0.85),
         "⚠ 数据打假：网传「每年 250 万人因乱服药入院、20 万人死亡」已被卫生部公开否认，来源不明，本项目不采用。\n"
         "我们只用可核验的官方口径：2025 年 65 岁以上 ADR 报告约 95 万份。",
         9.5, RGBColor(0x8A, 0x54, 0x10), spacing=1.6)
    footer(s, n)


# ------------------------------------------------------- 05 痛点三 用不上
def s05_pain_gap(prs, n):
    s = blank(prs)
    bg(s)
    page_title(s, "痛点三 · 用不上", "已有的适老化改造，停在「把字放大」",
               "政策已经变成法定义务，但供给与真实使用之间，还差最后一公里")
    rows = [
        ("政策要求", "《无障碍环境建设法》第三十七条：药品经营者应提供语音、大字、盲文等无障碍格式说明书（2023-09-01 施行）", TEAL, "已生效"),
        ("现实供给", "全国仅 1765 个品种参加试点，占全部批文比例极低；大字版仍需到店索取", AMBER, "供给不足"),
        ("数字鸿沟", "60 岁及以上互联网使用率仅 53.7%，近一半老人根本用不上 App（CNNIC 第 57 次报告）", RED, "入口缺失"),
        ("服务断层", "子女在外地、药师不在身边，「看不懂 → 不敢问 → 凭经验吃」的闭环没人打破", MUTED, "无人承接"),
    ]
    for i, (k, v, c, tag) in enumerate(rows):
        y = Inches(1.98) + Inches(0.95) * i
        rect(s, Inches(0.72), y, Inches(11.9), Inches(0.8), WHITE, LINE, radius=0.08)
        text(s, Inches(0.98), y + Inches(0.24), Inches(1.5), Inches(0.28), k, 11, c, True)
        text(s, Inches(2.6), y + Inches(0.16), Inches(9.0), Inches(0.5), v, 9.5, INK2, spacing=1.35)
        rect(s, Inches(11.35), y + Inches(0.22), Inches(1.0), Inches(0.34), TEAL_SOFT, None, radius=0.5)
        text(s, Inches(11.35), y + Inches(0.27), Inches(1.0), Inches(0.24), tag, 7.5, TEAL, True, align=PP_ALIGN.CENTER)
    rect(s, Inches(0.72), Inches(5.92), Inches(11.9), Inches(0.62), TEAL_SOFT, None, radius=0.1)
    text(s, Inches(1.0), Inches(6.08), Inches(11.3), Inches(0.34),
         "结论：政策给了「必须做」的理由，技术给了「能做到」的可能，中间缺一个「老人真的会用」的产品。", 10.5, TEAL, True)
    footer(s, n)


# ------------------------------------------------------------- 06 竞争格局
def s06_competitor(prs, n):
    s = blank(prs)
    bg(s)
    page_title(s, "竞争格局", "现有玩家都在做「说明书数字化」，没人做「用药决策」",
               "四个空白格，正好是我们的产品边界")
    headers = ["产品 / 方案", "说明书数字化", "AI 语音解读", "可溯源引用", "多药冲突", "家属协同"]
    data = [
        ("药监局说明书适老化试点", "✓", "—", "—", "—", "—"),
        ("阿里健康 / 支付宝大字版", "✓", "✓", "—", "—", "—"),
        ("通用 AI 助手（豆包/文心）", "—", "✓", "✗ 易编造", "—", "—"),
        ("用药提醒类 App", "—", "—", "—", "—", "部分"),
        ("安心药声（本项目）", "✓", "✓", "✓", "✓", "✓"),
    ]
    x0, y0 = Inches(0.72), Inches(1.95)
    widths = [Inches(3.42), Inches(1.72), Inches(1.56), Inches(1.52), Inches(1.42), Inches(1.36)]
    x = x0
    for w, htxt in zip(widths, headers):
        rect(s, x, y0, w, Inches(0.5), TEAL_SOFT)
        text(s, x + Inches(0.1), y0 + Inches(0.14), w - Inches(0.16), Inches(0.26), htxt, 9.5, TEAL, True,
             align=PP_ALIGN.CENTER if htxt != headers[0] else PP_ALIGN.LEFT)
        x += w
    for i, row in enumerate(data):
        y = y0 + Inches(0.5) + Inches(0.62) * i
        is_us = i == len(data) - 1
        x = x0
        for j, (w, val) in enumerate(zip(widths, row)):
            rect(s, x, y, w, Inches(0.62), TEAL_SOFT if is_us else WHITE, LINE)
            if j == 0:
                text(s, x + Inches(0.1), y + Inches(0.19), w - Inches(0.16), Inches(0.28), val,
                     9.5, INK if not is_us else TEAL, is_us)
            else:
                c = TEAL if val.startswith("✓") else (RED if "✗" in val else FAINT)
                text(s, x + Inches(0.1), y + Inches(0.19), w - Inches(0.16), Inches(0.28), val,
                     9.5 if val != "部分" else 8.5, c, val.startswith("✓") or is_us, align=PP_ALIGN.CENTER)
            x += w
    text(s, Inches(0.72), Inches(5.9), Inches(11.9), Inches(0.5),
         "注：截至 2025 年 12 月的公开资料调研。试点与平台型产品均以「提供大字/语音版本」为主，公开报道中未见多药冲突审核与家属端。",
         8, MUTED, spacing=1.4)
    footer(s, n)


# ------------------------------------------------------------- 07 解决方案
def s07_solution(prs, n):
    s = blank(prs)
    bg(s)
    page_title(s, "解决方案", "一个「会听、会看、会核」的用药安全助手",
               "四个能力对应四类真实场景，所有输出都能回到说明书原文")
    items = [
        ("01", "听懂说明书", "拍照 → 11 个字段结构化 → 四段式播报稿 → 慢速语音\n每句 ≤20 字，专业词当场解释", TEAL),
        ("02", "问明白", "RAG 检索 + 引用标注，答不上来就说不知道\n涉及停药 / 换药 / 加量，一律转医生", TEAL),
        ("03", "查冲突", "多药同服分级：禁忌 / 严重 / 注意 / 未见风险\n给出机制、后果与处置建议", AMBER),
        ("04", "连家人", "一键生成家属交接单：时间表、盯什么、何时送医", INK),
    ]
    for i, (num, title, body, c) in enumerate(items):
        col, row = i % 2, i // 2
        x = Inches(0.72) + Inches(6.12) * col
        y = Inches(1.98) + Inches(1.86) * row
        rect(s, x, y, Inches(5.78), Inches(1.64), WHITE, LINE, radius=0.06)
        text(s, x + Inches(0.26), y + Inches(0.2), Inches(0.8), Inches(0.4), num, 18, c, True)
        text(s, x + Inches(1.0), y + Inches(0.24), Inches(4.5), Inches(0.3), title, 14, INK, True)
        text(s, x + Inches(1.0), y + Inches(0.7), Inches(4.55), Inches(0.8), body, 9.5, INK2, spacing=1.55)
    footer(s, n)


# --------------------------------------------------------- 08-11 产品截图
def s_demo(prs, n, img, kicker, title, sub, points):
    s = blank(prs)
    bg(s)
    page_title(s, kicker, title, sub)
    if img.exists():
        pic = s.shapes.add_picture(str(img), Inches(0.72), Inches(1.98), width=Inches(7.55))
        if pic.height > Inches(4.55):
            r = Inches(4.55) / pic.height
            pic.height = Inches(4.55)
            pic.width = int(pic.width * r)
        pic.left = Inches(0.72)
    y = Inches(2.02)
    for h, b in points:
        rect(s, Inches(8.55), y, Inches(4.08), Inches(1.32), WHITE, LINE, radius=0.08)
        text(s, Inches(8.78), y + Inches(0.15), Inches(3.7), Inches(0.26), h, 11, TEAL, True)
        text(s, Inches(8.78), y + Inches(0.48), Inches(3.66), Inches(0.75), b, 8.5, INK2, spacing=1.45)
        y += Inches(1.5)
    footer(s, n)


# --------------------------------------------------------------- 12 架构
def s12_arch(prs, n):
    s = blank(prs)
    bg(s)
    page_title(s, "技术架构", "四层解耦：换模型、换病种，都不动业务代码",
               "视觉大模型做结构化，RAG 供证据，Agent 调工具，护栏管安全")
    img = SHOTS / "diagram_arch.png"
    if img.exists():
        pic = s.shapes.add_picture(str(img), Inches(0.55), Inches(1.92), width=Inches(12.25))
        if pic.height > Inches(4.55):
            r = Inches(4.55) / pic.height
            pic.height = Inches(4.55)
            pic.width = int(pic.width * r)
        pic.left = int((W - pic.width) / 2)
    footer(s, n)


# --------------------------------------------------------------- 13 Prompt
def s13_prompt(prs, n):
    s = blank(prs)
    bg(s)
    page_title(s, "技术深度 · 1", "Prompt 不是一句话，是一套「约束系统」",
               "6 个生产级 Prompt，全部采用「角色 + 任务 + 硬约束 + 输出结构 + 反例」五段式")
    rows = [
        ("说明书解析", "禁止知识补全", "缺失字段必须返回 null，每个字段附 evidence 原文锚点", TEAL),
        ("播报稿生成", "数字白名单", "数字与结构化字段逐字一致，生成后再做一次数字比对", AMBER),
        ("RAG 问答", "无证据不回答", "只允许用证据回答，句末必须标 [n]，3 条 few-shot 教它说不知道", TEAL),
        ("答案复核", "独立 Verifier", "另起一次调用逐句核对数字 / 断言 / 引用 / 风险，不通过则回退", RED),
        ("多药冲突", "四级分级", "禁忌 / 严重 / 注意 / 未见风险，必须给机制与后果，不许编相互作用", AMBER),
    ]
    for i, (name, key, body, c) in enumerate(rows):
        y = Inches(1.95) + Inches(0.88) * i
        rect(s, Inches(0.72), y, Inches(11.9), Inches(0.74), WHITE, LINE, radius=0.08)
        rect(s, Inches(0.72), y, Inches(0.06), Inches(0.74), c)
        text(s, Inches(0.98), y + Inches(0.22), Inches(1.8), Inches(0.28), name, 11, INK, True)
        text(s, Inches(2.85), y + Inches(0.22), Inches(1.9), Inches(0.28), key, 9.5, c, True)
        text(s, Inches(4.85), y + Inches(0.2), Inches(7.6), Inches(0.4), body, 9, INK2, spacing=1.3)
    rect(s, Inches(0.72), Inches(6.34), Inches(11.9), Inches(0.44), TEAL_SOFT, None, radius=0.1)
    text(s, Inches(0.98), Inches(6.44), Inches(11.4), Inches(0.26),
         "迭代实证：v1 纯规则 → 证据充分仍拒答；v2 加 3 条 few-shot → 行为符合率显著提升；v3 加「常识可引用需声明」→ 超纲问题可用且不越界。",
         8.5, TEAL, True)
    footer(s, n)


# ---------------------------------------------------------------- 14 Agent
def s14_agent(prs, n):
    s = blank(prs)
    bg(s)
    page_title(s, "技术深度 · 2", "Agent 会自己决定「查什么」，而不是背答案",
               "Function Calling 最多 5 轮，每次工具调用都留痕，可审计、可复现")
    steps = [
        ("用户提问", "「我同时在吃克拉霉素，这两个药能一起吃吗？」", FAINT),
        ("第 1 次调用", "search_label(query=用法用量 / 禁忌 / 相互作用)", TEAL),
        ("第 2 次调用", "check_interaction(阿托伐他汀钙片, 克拉霉素)", AMBER),
        ("证据回灌", "说明书原文 + 知识库 KB001（等级：严重）", TEAL),
        ("生成 + 复核", "四道闸门 → 独立 Verifier → 输出带引用的回答", INK),
    ]
    for i, (k, v, c) in enumerate(steps):
        y = Inches(1.95) + Inches(0.84) * i
        rect(s, Inches(0.72), y, Inches(7.0), Inches(0.7), WHITE, LINE, radius=0.08)
        text(s, Inches(0.96), y + Inches(0.21), Inches(1.55), Inches(0.26), k, 9.5, c, True)
        text(s, Inches(2.55), y + Inches(0.2), Inches(5.0), Inches(0.34), v, 8.8, INK2)

    rect(s, Inches(8.1), Inches(1.95), Inches(4.52), Inches(3.96), DARK, None, radius=0.05)
    text(s, Inches(8.38), Inches(2.16), Inches(4.0), Inches(0.26), "运行日志（节选）", 8.5, RGBColor(0x7F, 0xB0, 0xA4), True)
    log = ("POST /api/agent          4.6s\n\n"
           "→ tool search_label     812ms\n"
           "→ tool check_interaction  3ms\n"
           "     hit KB001 · level=严重\n"
           "→ guard numbers        pass\n"
           "→ guard citations      pass\n"
           "→ verifier             pass\n\n"
           "✓ 返回回答（含 2 条引用）")
    text(s, Inches(8.38), Inches(2.56), Inches(4.0), Inches(3.0), log, 8.5,
         RGBColor(0x9F, 0xE0, 0xCB), spacing=1.55, font="Consolas")

    rect(s, Inches(0.72), Inches(6.18), Inches(11.9), Inches(0.52), AMBER_SOFT, None, radius=0.1)
    text(s, Inches(0.98), Inches(6.31), Inches(11.4), Inches(0.3),
         "5 个工具：search_label · check_interaction · get_elderly_tip · set_med_reminder · escalate_to_human", 8.8,
         RGBColor(0x8A, 0x54, 0x10), True)
    footer(s, n)


# ---------------------------------------------------------------- 15 护栏
def s15_guard(prs, n, summary):
    s = blank(prs)
    bg(s)
    page_title(s, "技术深度 · 3", "让大模型「不敢乱说」：四道闸门 + 可量化评测",
               "医疗场景里，能说「不知道」比说得多更重要")
    gates = [
        ("① 数字接地", "答案中的数字+单位必须命中证据原文", RED_SOFT, RED),
        ("② 引用校验", "[n] 必须落在召回编号范围内", AMBER_SOFT, AMBER),
        ("③ 危险拦截", "停药 / 换药 / 加量 / 诊断 → 强制改写", TEAL_SOFT, TEAL),
        ("④ 独立复核", "第二次模型调用逐句核对，不通过则回退", RGBColor(0xEF, 0xF4, 0xF2), INK),
    ]
    for i, (t, d, c1, c2) in enumerate(gates):
        y = Inches(1.95) + Inches(0.86) * i
        rect(s, Inches(0.72), y, Inches(5.7), Inches(0.72), c1, None, radius=0.08)
        text(s, Inches(0.96), y + Inches(0.2), Inches(1.7), Inches(0.28), t, 10, c2, True)
        text(s, Inches(2.72), y + Inches(0.21), Inches(3.5), Inches(0.3), d, 8.5, INK2)

    rect(s, Inches(6.8), Inches(1.95), Inches(5.82), Inches(3.55), WHITE, LINE, radius=0.05)
    text(s, Inches(7.05), Inches(2.13), Inches(5.0), Inches(0.28), "20 条评测集 · 实测结果", 10.5, TEAL, True)
    metrics = [
        ("安全率（不出现禁止内容）", summary.get("safety_rate")),
        ("行为符合率（该答就答、该拒就拒）", summary.get("behavior_rate")),
        ("关键信息准确率", summary.get("accuracy")),
        ("引用覆盖率", summary.get("citation_rate")),
        ("数字幻觉率（越低越好）", summary.get("number_hallucination_rate")),
    ]
    for i, (k, v) in enumerate(metrics):
        y = Inches(2.55) + Inches(0.58) * i
        text(s, Inches(7.05), y, Inches(3.9), Inches(0.26), k, 8.5, INK2)
        val = f"{v*100:.0f}%" if isinstance(v, (int, float)) else "—"
        text(s, Inches(11.0), y - Inches(0.05), Inches(1.35), Inches(0.28), val, 12.5,
             TEAL if (v or 0) >= 0.85 else AMBER, True, align=PP_ALIGN.RIGHT)
        rect(s, Inches(7.05), y + Inches(0.27), Inches(5.3), Inches(0.05), RGBColor(0xEF, 0xF4, 0xF2))
        if isinstance(v, (int, float)):
            rect(s, Inches(7.05), y + Inches(0.27), Inches(5.3 * min(1, v)), Inches(0.05), TEAL if v >= 0.85 else AMBER)

    rect(s, Inches(0.72), Inches(5.72), Inches(11.9), Inches(0.82), TEAL_SOFT, None, radius=0.08)
    text(s, Inches(0.98), Inches(5.88), Inches(11.4), Inches(0.5),
         "对照实验：去掉护栏后，同一批用例出现三类问题 —— 编造剂量、把「慎用」说成「禁用」、给出停药建议。",
         9.5, TEAL, True)
    footer(s, n)


# ---------------------------------------------------------------- 16 壁垒
def s16_moat(prs, n):
    s = blank(prs)
    bg(s)
    page_title(s, "技术壁垒", "壁垒不在模型，在「数据 + 约束 + 场景」的三层沉淀",
               "模型谁都能调，但「不敢乱说」的工程体系和「老人真的会用」的交互，抄不走")
    cols = [
        ("数据层", "说明书结构化语料（含 evidence 锚点）\n人工校核的相互作用知识库\n老年口语问答数据集", "冷启动最难：\n需要时间与药师资源"),
        ("约束层", "四道闸门 + 独立 Verifier\n数字白名单\n四级冲突分级标准", "方法论可迁移：\n换病种只需换知识库"),
        ("场景层", "适老化交互规范\n家属协同链路\n药店 / 药师服务网络", "网络效应：\n药店越多，数据越厚"),
    ]
    for i, (t, body, note) in enumerate(cols):
        x = Inches(0.72) + Inches(4.03) * i
        rect(s, x, Inches(1.95), Inches(3.78), Inches(2.85), WHITE, LINE, radius=0.06)
        text(s, x + Inches(0.28), Inches(2.15), Inches(3.2), Inches(0.3), t, 13, TEAL, True)
        text(s, x + Inches(0.28), Inches(2.62), Inches(3.25), Inches(1.2), body, 9.5, INK2, spacing=1.6)
        rect(s, x + Inches(0.28), Inches(3.92), Inches(3.2), Inches(0.015), LINE)
        text(s, x + Inches(0.28), Inches(4.04), Inches(3.25), Inches(0.6), note, 8.5, FAINT, spacing=1.4)

    rect(s, Inches(0.72), Inches(5.1), Inches(11.9), Inches(1.42), TEAL_SOFT, None, radius=0.06)
    text(s, Inches(0.98), Inches(5.26), Inches(2.6), Inches(0.28), "可运行原型（加分项）", 10.5, TEAL, True)
    text(s, Inches(0.98), Inches(5.6), Inches(11.3), Inches(0.8),
         "完整代码开源：FastAPI + 原生前端，零构建步骤，clone 即跑；20 条评测集与 10 项冒烟测试可一键复跑；\n"
         "已实测接入火山方舟、任意 OpenAI-Compatible 服务与本地 Ollama 三种部署形态。", 9, INK2, spacing=1.6)
    footer(s, n)


# ---------------------------------------------------------------- 17 市场
def s17_market(prs, n):
    s = blank(prs)
    bg(s)
    page_title(s, "市场分析", "银发经济 7 万亿，用药安全是最高频的切口",
               "不追风口，只算一笔账：一个老人一年在药上花多少钱，其中多少是「本可以避免的错误」")
    layers = [
        ("TAM 全国", "3.23 亿 60+ 人口  ·  银发经济约 7 万亿元", 12.0, Inches(1.95), RGBColor(0xD8, 0xEE, 0xE7), INK),
        ("SAM 目标", "约 1.4 亿慢病长期用药老人  ·  目标家庭约 4000 万户", 8.6, Inches(2.7), RGBColor(0xB6, 0xE2, 0xD5), INK),
        ("SOM 3 年", "10 城 · 50 万用户 · 8% 付费率 ≈ 470 万元/年", 5.2, Inches(3.45), TEAL, WHITE),
    ]
    for t, body, w_in, y, c, colr in layers:
        w = Inches(w_in)
        x = int((W - w) / 2)
        rect(s, x, y, w, Inches(0.66), c, None, radius=0.3)
        text(s, x + Inches(0.35), y + Inches(0.13), Inches(1.7), Inches(0.28), t, 10, colr, True)
        text(s, x + Inches(2.1), y + Inches(0.15), w - Inches(2.4), Inches(0.3), body, 8.5, colr)

    text(s, Inches(0.72), Inches(4.3), Inches(11.9), Inches(0.26),
         "测算口径：60+ 人口 3.23 亿（民政部 2025 年公报）；银发经济约 7 万亿元、占 GDP 约 6%（银发经济蓝皮书 2024）",
         7.8, MUTED)
    rect(s, Inches(0.72), Inches(4.78), Inches(11.9), Inches(1.75), WHITE, LINE, radius=0.05)
    text(s, Inches(0.98), Inches(4.94), Inches(3), Inches(0.28), "为什么是现在", 10.5, TEAL, True)
    pts = [
        "政策：无障碍环境建设法 2023 年施行，说明书无障碍格式成为法定义务",
        "技术：多模态模型成本一年降一个数量级，单次解读成本已低于 0.01 元",
        "人口：2025 年 60+ 人口 3.23 亿、占 23.0%，子女异地化程度高，付费意愿真实存在",
    ]
    for i, p in enumerate(pts):
        text(s, Inches(0.98), Inches(5.32) + Inches(0.32) * i, Inches(11.4), Inches(0.28), "· " + p, 8.8, INK2)
    footer(s, n)


# ---------------------------------------------------------------- 18 商业
def s18_business(prs, n):
    s = blank(prs)
    bg(s)
    page_title(s, "商业模式", "不向老人收费，向「关心老人的人」收费",
               "老人是使用者，子女是付费者，药店是渠道")
    cells = [
        ("客户细分", "C 端付费：异地子女（25~45 岁）\nC 端使用：60+ 慢病老人\nB 端：连锁药店、社区养老机构\nG 端：医保 / 卫健适老化项目"),
        ("价值主张", "子女：远程看得见父母的用药\n老人：听得懂、看得清、有人管\n药店：多一个到店理由与服务抓手"),
        ("收入来源", "子女端订阅 9.9 元/月（99 元/年）\n药店 SaaS 3000 元/店/年\nG 端项目制 20~80 万元/项目"),
        ("核心资源", "说明书结构化语料\n人工校核的相互作用知识库\n药师网络与适老化交互规范"),
        ("关键活动", "说明书解析与评测\n药师复核工单\n社区义诊 / 药店驻点"),
        ("成本结构", "模型调用 <0.01 元/次\n语音合成免费\n人力以药师复核与地推为主"),
    ]
    for i, (t, body) in enumerate(cells):
        col, row = i % 3, i // 3
        x = Inches(0.72) + Inches(4.05) * col
        y = Inches(1.95) + Inches(2.05) * row
        rect(s, x, y, Inches(3.8), Inches(1.85), WHITE, LINE, radius=0.06)
        text(s, x + Inches(0.26), y + Inches(0.18), Inches(3.3), Inches(0.28), t, 10.5, TEAL, True)
        text(s, x + Inches(0.26), y + Inches(0.6), Inches(3.35), Inches(1.1), body, 8.8, INK2, spacing=1.55)
    rect(s, Inches(0.72), Inches(6.12), Inches(11.9), Inches(0.52), TEAL_SOFT, None, radius=0.1)
    text(s, Inches(0.98), Inches(6.24), Inches(11.4), Inches(0.28),
         "单位经济模型：年费 118 元，目标获客成本 < 40 元，毛利 > 70%，回本周期约 5 个月", 9, TEAL, True)
    footer(s, n)


# ------------------------------------------------------------ 19 增长+价值
def s19_growth(prs, n):
    s = blank(prs)
    bg(s)
    page_title(s, "增长路径与社会价值", "从「一个社区」到「一张网」，也从「一个家庭」到「一代人」")
    phases = [
        ("0-6 个月", "种子验证", ["1 个社区 + 2 家药店", "200 位老人免费试用", "播报完成率 > 60%"], TEAL),
        ("6-18 个月", "模式复制", ["10 城 · 200 家药店", "子女端订阅上线", "进地方适老化目录"], AMBER),
        ("18-36 个月", "网络效应", ["药师复核工单平台", "区域知识库共建", "向慢病管理延伸"], INK),
    ]
    for i, (t, sub, items, c) in enumerate(phases):
        x = Inches(0.72) + Inches(4.03) * i
        rect(s, x, Inches(1.9), Inches(3.78), Inches(0.64), c, None, radius=0.14)
        text(s, x + Inches(0.22), Inches(2.02), Inches(1.3), Inches(0.28), t, 8.5, WHITE, True)
        text(s, x + Inches(1.5), Inches(2.02), Inches(2.1), Inches(0.28), sub, 9.5, WHITE, True)
        for j, it in enumerate(items):
            text(s, x + Inches(0.2), Inches(2.68) + Inches(0.3) * j, Inches(3.5), Inches(0.28), "· " + it, 8.5, INK2)

    rect(s, Inches(0.72), Inches(3.66), Inches(11.9), Inches(2.55), WHITE, LINE, radius=0.05)
    text(s, Inches(0.98), Inches(3.84), Inches(4), Inches(0.28), "社会效益（可量化）", 10.5, TEAL, True)
    vals = [
        ("3.23 亿", "60+ 人口，其中慢病长期用药者约 1.4 亿"),
        ("1731 万", "视障人群可获得「可听」的说明书"),
        ("≈6 万元/年", "每 1000 位老人减少 1 次可避免用药事件，可节省的医保支出（测算）"),
    ]
    for i, (num, lab) in enumerate(vals):
        y = Inches(4.22) + Inches(0.6) * i
        text(s, Inches(0.98), y, Inches(1.6), Inches(0.32), num, 14, INK, True)
        text(s, Inches(2.72), y + Inches(0.05), Inches(9.6), Inches(0.3), lab, 9, INK2)
    text(s, Inches(0.98), Inches(5.92), Inches(11.3), Inches(0.26),
         "定位：不是「帮老人省事」的工具，而是「减少可避免伤害」的公共基础设施。", 9.5, TEAL, True)
    footer(s, n)


# --------------------------------------------------------------- 20 团队
def s20_team(prs, n):
    s = blank(prs)
    bg(s)
    page_title(s, "团队与路线图", "会写代码，也进过社区")
    members = [
        ("郭翰林", "项目负责人 / 全栈", "架构、模型接入、前端"),
        ("郭翰林", "算法", "Prompt 工程与评测体系"),
        ("待定", "药学顾问", "执业药师，知识库校核"),
        ("郭翰林", "产品运营", "社区地推与用户访谈"),
    ]
    for i, (name, role, desc) in enumerate(members):
        x = Inches(0.72) + Inches(2.98) * i
        rect(s, x, Inches(1.88), Inches(2.78), Inches(1.4), WHITE, LINE, radius=0.07)
        text(s, x + Inches(0.22), Inches(2.0), Inches(2.3), Inches(0.28), name, 10.5, INK, True)
        text(s, x + Inches(0.22), Inches(2.3), Inches(2.3), Inches(0.26), role, 8, TEAL)
        text(s, x + Inches(0.22), Inches(2.6), Inches(2.35), Inches(0.55), desc, 8, MUTED, spacing=1.4)

    rows = [
        ("2026 Q4", "v1.0", "拍照解析 / 语音播报 / 有据问答 / 多药冲突 / 家属单"),
        ("2027 Q1", "v1.1", "方言语音（粤语、川渝）、离线小模型端侧部署"),
        ("2027 Q2", "v1.2", "药盒条码与追溯码识别，对接国家药品编码"),
        ("2027 Q3", "v1.3", "药店 / 家庭医生协作台，药师复核工单"),
    ]
    for i, (t, v, body) in enumerate(rows):
        y = Inches(3.52) + Inches(0.58) * i
        text(s, Inches(0.75), y + Inches(0.06), Inches(1.2), Inches(0.26), t, 8.5, TEAL, True)
        text(s, Inches(1.95), y + Inches(0.06), Inches(0.7), Inches(0.26), v, 8.5, INK, True)
        text(s, Inches(2.7), y + Inches(0.06), Inches(5.3), Inches(0.26), body, 8.3, INK2)
        rect(s, Inches(0.75), y + Inches(0.4), Inches(7.2), Inches(0.012), LINE)

    rect(s, Inches(8.3), Inches(3.46), Inches(4.32), Inches(2.35), WHITE, LINE, radius=0.05)
    text(s, Inches(8.54), Inches(3.6), Inches(3.9), Inches(0.28), "风险与应对", 10, RED, True)
    risks = [("医疗合规", "定位信息无障碍工具，不做诊断"),
             ("幻觉风险", "四道闸门 + 独立复核，高危转人工"),
             ("用户获取", "先 B 端药店，带到店服务"),
             ("数据来源", "只解析用户上传内容，不训练")]
    for i, (k, v) in enumerate(risks):
        y = Inches(4.0) + Inches(0.42) * i
        text(s, Inches(8.54), y, Inches(1.0), Inches(0.24), k, 7.8, INK, True)
        text(s, Inches(9.58), y, Inches(2.9), Inches(0.24), v, 7.6, INK2)

    rect(s, Inches(0.72), Inches(6.0), Inches(11.9), Inches(0.72), DARK, None, radius=0.12)
    text(s, Inches(1.0), Inches(6.18), Inches(11.3), Inches(0.36),
         "让每一位老人，都听得懂自己吃的药。 —— 安心药声", 11.5, RGBColor(0x8F, 0xE0, 0xC9), True)
    footer(s, n)


def main() -> None:
    summary = {}
    ev = ROOT / "app" / "eval" / "eval_report.json"
    if ev.exists():
        summary = json.loads(ev.read_text(encoding="utf-8-sig")).get("summary", {})

    prs = new_deck()
    s01_cover(prs)
    s02_persona(prs, 2)
    s03_pain_vision(prs, 3)
    s04_pain_mix(prs, 4)
    s05_pain_gap(prs, 5)
    s06_competitor(prs, 6)
    s07_solution(prs, 7)
    s_demo(prs, 8, SHOTS / "02_parse.png", "产品演示 · 1", "拍一张照片，11 个字段自动拆好",
           "每个字段都能展开看原文，识别不准会明确告诉你「置信度下降」",
           [("结构化输出", "适应症 / 用法用量 / 禁忌 / 不良反应 / 相互作用等 11 个字段"),
            ("原文锚点", "每个字段附带 evidence，点开即见说明书原句"),
            ("置信度提示", "低于 75% 提示重拍或转药师，不硬猜")])
    s_demo(prs, 9, SHOTS / "03_playback.png", "产品演示 · 2", "不只是朗读，是「重新讲一遍」",
           "四段式播报稿，每句不超过 20 字，语速放慢 12%，数字自动转中文读法",
           [("四段结构", "治什么 / 怎么吃 / 当心什么 / 何时就医"),
            ("逐段高亮", "播到哪一段，文字同步高亮，听不清还能看"),
            ("数字读法", "20mg 读作「二十毫克」，不是「二十 M G」")])
    s_demo(prs, 10, SHOTS / "06_agent.png", "产品演示 · 3", "每个回答都能点回原文",
           "Agent 自动调检索与相互作用工具；证据不足时直接说「说明书里没写」",
           [("引用可溯源", "句末的 [n] 对应证据编号，悬停即见原文"),
            ("工具留痕", "右侧完整展示模型调了哪些工具、耗时多少"),
            ("该拒就拒", "停药 / 换药 / 加量 / 诊断，一律转医生")])
    s_demo(prs, 11, SHOTS / "08_mix.png", "产品演示 · 4", "两种药能不能一起吃？分级告诉你",
           "禁忌 / 严重 / 注意 / 未见风险 四级，给出机制、后果与处置",
           [("知识库 + 模型", "说明书原文 + 人工校核的相互作用知识库"),
            ("分级呈现", "红色禁忌、橙色注意，老人也看得懂"),
            ("家属同步", "一键生成交接单，子女远程看得懂")])
    s12_arch(prs, 12)
    s13_prompt(prs, 13)
    s14_agent(prs, 14)
    s15_guard(prs, 15, summary)
    s16_moat(prs, 16)
    s17_market(prs, 17)
    s18_business(prs, 18)
    s19_growth(prs, 19)
    s20_team(prs, 20)

    out = OUT / "安心药声-商业计划书.pptx"
    prs.save(str(out))
    print("saved", out)


if __name__ == "__main__":
    main()
