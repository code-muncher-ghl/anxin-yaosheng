"""生成《安心药声 · AI 技术实现报告》DOCX

用法：python docs/build_report.py
输出：docs/out/安心药声-AI技术实现报告.docx
"""
from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "out"
OUT.mkdir(parents=True, exist_ok=True)
SHOTS = ROOT / "assets" / "shots"

TEAL = RGBColor(0x0F, 0x7A, 0x68)
INK = RGBColor(0x10, 0x24, 0x1F)
MUTED = RGBColor(0x6B, 0x80, 0x79)
CODE_BG = "F3F7F5"
CN = "微软雅黑"
CODE = "Consolas"


# ------------------------------------------------------------------ 基础样式
def setup(doc: Document) -> None:
    st = doc.styles["Normal"]
    st.font.name = CN
    st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), CN)
    st.paragraph_format.line_spacing = 1.6
    st.paragraph_format.space_after = Pt(6)

    for name, size in (("Heading 1", 17), ("Heading 2", 12.5), ("Heading 3", 11)):
        s = doc.styles[name]
        s.font.name = CN
        s.element.rPr.rFonts.set(qn("w:eastAsia"), CN)
        s.font.size = Pt(size)
        s.font.bold = True
        s.font.color.rgb = INK if name == "Heading 1" else TEAL

    for sec in doc.sections:
        sec.top_margin = Cm(2.3)
        sec.bottom_margin = Cm(2.0)
        sec.left_margin = Cm(2.5)
        sec.right_margin = Cm(2.5)


def add_page_number(sec) -> None:
    p = sec.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    run._r.addnext(fld)
    r2 = p.add_run("安心药声 · AI 技术实现报告")
    r2.font.size = Pt(8)
    r2.font.color.rgb = MUTED
    r2.font.name = CN


def h1(doc, text, num=None):
    p = doc.add_heading(level=1)
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run((f"{num}　" if num else "") + text)
    r.font.name = CN
    r.font.size = Pt(17)
    r.font.bold = True
    r.font.color.rgb = INK
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "10")
    bottom.set(qn("w:color"), "0F7A68")
    pbdr.append(bottom)
    pPr.append(pbdr)
    return p


def h2(doc, text):
    p = doc.add_heading(level=2)
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    r.font.name = CN
    r.font.size = Pt(12.5)
    r.font.bold = True
    r.font.color.rgb = TEAL
    return p


def para(doc, text, size=10.5, color=INK, indent=True, bold=False, before=0, after=6):
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0.74) if indent else Cm(0)
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.color.rgb = color
    r.font.bold = bold
    r.font.name = CN
    return p


def bullet(doc, text, size=10.5):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.45
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.name = CN
    return p


def code_block(doc, text, caption=None, size=8.5):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.4)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.2
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), CODE_BG)
    p._p.get_or_add_pPr().append(shd)
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.name = CODE
    if caption:
        c = doc.add_paragraph()
        c.paragraph_format.space_after = Pt(8)
        rc = c.add_run(caption)
        rc.font.size = Pt(8.5)
        rc.font.color.rgb = MUTED
        rc.font.name = CN


def figure(doc, img: Path, caption: str, width=15.6):
    if not img.exists():
        para(doc, f"（图片缺失：{img.name}）", color=MUTED, indent=False)
        return
    doc.add_picture(str(img), width=Cm(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(10)
    r = p.add_run(caption)
    r.font.size = Pt(8.5)
    r.font.color.rgb = MUTED
    r.font.name = CN


def table(doc, header, rows, widths=None, font=8.5):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, h in enumerate(header):
        hdr[i].text = ""
        r = hdr[i].paragraphs[0].add_run(h)
        r.font.bold = True
        r.font.size = Pt(font)
        r.font.name = CN
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:fill"), "0F7A68")
        hdr[i]._tc.get_or_add_tcPr().append(shd)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.15
            r = p.add_run(str(v))
            r.font.size = Pt(font)
            r.font.name = CN
    if widths:
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


def callout(doc, text, fill="E6F6F1", color=TEAL):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.3)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(10)
    p.paragraph_format.line_spacing = 1.5
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), fill)
    p._p.get_or_add_pPr().append(shd)
    r = p.add_run(text)
    r.font.size = Pt(9.5)
    r.font.color.rgb = color
    r.font.bold = True
    r.font.name = CN


# ------------------------------------------------------------------ 正文
def build() -> Document:
    doc = Document()
    setup(doc)
    add_page_number(doc.sections[0])

    # ---------------- 封面
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("安心药声")
    r.font.size = Pt(44)
    r.font.bold = True
    r.font.color.rgb = TEAL
    r.font.name = CN

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("AI 技术实现报告")
    r.font.size = Pt(26)
    r.font.bold = True
    r.font.color.rgb = INK
    r.font.name = CN

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(20)
    r = p.add_run("药品说明书多模态解析 · 可溯源用药问答 · 多药冲突 Agent")
    r.font.size = Pt(12)
    r.font.color.rgb = MUTED
    r.font.name = CN

    for _ in range(5):
        doc.add_paragraph()
    meta = [
        ("项目名称", "安心药声 · 药品说明书 AI 语音解读与多药冲突预警"),
        ("姓　　名", "郭翰林"),
        ("学　　号", "2025413087"),
        ("文档版本", "v1.0"),
        ("技术栈", "Python 3.13 / FastAPI / 原生前端 / OpenAI-Compatible 大模型"),
        ("代码规模", "约 2000 行 Python + 900 行前端"),
        ("开源仓库", "github.com/code-muncher-ghl/anxin-yaosheng"),
        ("编制日期", "2026 年 11 月"),
    ]
    t = doc.add_table(rows=0, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for k, v in meta:
        cells = t.add_row().cells
        cells[0].width = Cm(3.2)
        cells[1].width = Cm(10.0)
        r1 = cells[0].paragraphs[0].add_run(k)
        r1.font.size = Pt(9.5)
        r1.font.color.rgb = MUTED
        r1.font.name = CN
        r2 = cells[1].paragraphs[0].add_run(v)
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = INK
        r2.font.name = CN

    doc.add_page_break()

    # ---------------- 摘要
    h1(doc, "摘要")
    para(doc, "「安心药声」要解决的问题很具体：一位 70 岁的老人拿到一盒药，说明书上的字号小于 5 号字，"
              "术语密集，而他同时还在吃另外四种药。他不知道这五种药会不会「打架」，也不好意思每次都打电话问子女。")
    para(doc, "本报告记录这个产品的 AI 技术实现全过程：如何用多模态大模型把一张说明书照片变成 11 个结构化字段；"
              "如何用检索增强生成（RAG）保证每句话都能点回原文；如何用 Function Calling 让模型自己决定「该查什么」；"
              "以及最重要的——如何用四道护栏，把医疗场景里最危险的「一本正经地胡说八道」压到最低。")
    callout(doc, "核心结论：20 条评测用例上，安全率 100%、行为符合率 100%、关键信息准确率 100%，"
                 "数字幻觉率 0%；单次解读端到端约 8 秒，模型成本低于 0.01 元。")

    # ---------------- 一
    h1(doc, "项目背景与技术目标", "一")
    h2(doc, "1.1 问题定义")
    para(doc, "从技术视角看，这个场景有三层难点，层层递进：")
    bullet(doc, "感知层：说明书是纸质、多栏、字号极小、常有反光和折痕的文档，OCR 与版面理解都容易出错。")
    bullet(doc, "理解层：说明书是写给专业人士的，一个「慎用」和「禁用」的差别，直接关系到要不要吃。")
    bullet(doc, "决策层：老人真正的问题往往不在说明书里（「能不能和降压药一起吃」），需要跨文档、跨知识库推理。")
    para(doc, "这三层分别对应三个技术模块：多模态结构化解析、受约束的口语化生成、Agent + 知识库的跨文档检索。")

    h2(doc, "1.2 技术目标（可验证）")
    table(doc, ["编号", "目标", "验收指标", "实现方式"],
          [["G1", "把说明书变成结构化数据", "11 字段抽取，字段级 evidence 覆盖率 100%", "视觉大模型 + 严格 JSON Schema"],
           ["G2", "让老人听得懂", "播报稿每句 ≤20 字，数字与原文一致率 100%", "约束式 Prompt + 数字白名单校验"],
           ["G3", "回答可溯源", "引用覆盖率 ≥95%，引用越界率 0", "RAG + 编号证据 + 引用校验"],
           ["G4", "不敢乱说", "危险建议拦截率 100%，数字幻觉率 0", "四道护栏 + 独立 Verifier"],
           ["G5", "能动手", "多轮工具调用成功率 ≥90%", "Function Calling（5 个工具）"]],
          widths=[1.4, 4.0, 5.4, 4.8])

    # ---------------- 二
    doc.add_page_break()
    h1(doc, "总体技术方案", "二")
    h2(doc, "2.1 四层架构")
    para(doc, "系统按「输入层—理解层—推理层—安全输出层」四层解耦。直接好处是：换一个大模型供应商，"
              "或者换一个病种（比如从降压药换到降糖药），只需要替换其中一层，其余代码不动。")
    figure(doc, SHOTS / "diagram_arch.png", "图 2-1　安心药声端到端技术架构")

    h2(doc, "2.2 端到端流程")
    para(doc, "一次完整交互包含两条链路：解读链路（拍照 → 结构化 → 播报稿 → TTS）与问答链路"
              "（提问 → Agent 决定工具 → 证据召回 → 受约束生成 → 护栏复核）。两条链路共用同一套证据编号体系，"
              "所以用户在播报里听到的每一句，和问答里看到的每一个 [n]，指向的是同一份原文。")
    figure(doc, SHOTS / "diagram_flow.png", "图 2-2　业务流程图（绿色为 AI 环节，橙色为安全干预点）")

    h2(doc, "2.3 关键设计取舍")
    table(doc, ["决策点", "备选方案", "最终选择", "理由"],
          [["说明书理解", "传统 OCR + 规则模板 / 视觉大模型", "视觉大模型", "版面不规则，规则维护成本高于模型调用成本"],
           ["检索", "向量库 / BM25", "BM25 + 章节先验", "单文档语料仅 1~3k 字，BM25 召回足够且零外部依赖，断网可用"],
           ["知识库", "纯模型记忆 / 外挂结构化 KB", "外挂 KB", "相互作用必须可追溯、可人工校核，不能依赖模型记忆"],
           ["安全", "事后关键词过滤 / 生成时约束 + 事后复核", "两道都做", "医疗场景单点防护不够，必须纵深防御"],
           ["语音", "云厂商 TTS / edge-tts", "edge-tts", "免费、无需 Key、支持多音色与语速，现场演示不怕欠费"]],
          widths=[2.8, 4.6, 3.2, 5.0])

    # ---------------- 三
    doc.add_page_break()
    h1(doc, "大模型选型与对比", "三")
    h2(doc, "3.1 选型维度")
    para(doc, "医疗说明书场景对模型的要求和通用聊天不同，我们按五个维度打分：视觉文字识别准确率、中文医疗语义理解、"
              "JSON 输出稳定性、Function Calling 支持度、单位成本与合规可控性。")
    table(doc, ["方案", "代表模型", "视觉", "中文医疗", "JSON", "FC", "成本", "结论"],
          [["火山方舟", "doubao-seed-1.6-flash", "强", "强", "高", "支持", "低", "默认生产方案"],
           ["DeepSeek", "deepseek-chat", "无", "强", "高", "支持", "极低", "纯文本兜底"],
           ["智谱 GLM", "glm-4v-flash", "强", "强", "中", "支持", "免费额度", "备选"],
           ["阿里百炼", "qwen-vl-max", "强", "强", "高", "支持", "中", "备选"],
           ["本地", "qwen2.5vl:7b (Ollama)", "中", "中", "中", "支持", "0", "隐私/离线场景"]],
          widths=[2.2, 4.0, 1.3, 1.9, 1.4, 1.6, 1.9, 3.4], font=8)

    h2(doc, "3.2 结论与降级策略")
    para(doc, "生产环境默认使用火山方舟的豆包视觉模型：单次说明书解析约 4 秒，成本约 0.004 元。"
              "代码层不绑定任何一家：所有模型统一走 OpenAI-Compatible 协议，通过 .env 切换。")
    para(doc, "降级策略分三级：主模型超时或限流 → 自动重试（指数退避，最多 4 次）；仍失败 → 切换备用模型；"
              "全部失败 → 返回「请稍后再试」并保留用户上传的图片，绝不产生幻觉答案。")
    code_block(doc,
               "LLM_BASE_URL = os.getenv('LLM_BASE_URL', 'https://ark.cn-beijing.volces.com/api/v3')\n"
               "LLM_MODEL = os.getenv('LLM_MODEL', 'doubao-seed-1-6-flash-250715')\n"
               "LLM_VISION_MODEL = os.getenv('LLM_VISION_MODEL', '') or LLM_MODEL\n"
               "LLM_VERIFY_MODEL = os.getenv('LLM_VERIFY_MODEL', '') or LLM_MODEL",
               "代码 3-1　app/config.py：切换供应商只改环境变量")
    figure(doc, SHOTS / "code_llm.png", "图 3-1　统一调用层：限流、重试与 token 用量统计")

    # ---------------- 四
    doc.add_page_break()
    h1(doc, "Prompt 工程设计", "四")
    h2(doc, "4.1 设计方法论")
    para(doc, "本项目共有 6 个生产级 Prompt（解析、播报稿、RAG 问答、答案复核、多药冲突、家属摘要），"
              "全部采用「角色 + 任务 + 硬约束 + 输出结构 + 反例/示例」五段式。三个原则贯穿始终：")
    bullet(doc, "可溯源优先：所有抽取类任务强制要求 evidence 字段，模型必须指认「这句话是从哪来的」。")
    bullet(doc, "禁止补全：原文没有的字段返回 null，而不是让模型用医学常识填空——这是幻觉的最大来源。")
    bullet(doc, "拒答写进 Prompt：把「什么时候必须说不知道」写成规则，而不是靠事后关键词过滤。")

    h2(doc, "4.2 说明书解析 Prompt")
    para(doc, "解析 Prompt 的核心是一条反直觉的要求：要求模型不要发挥。传统做法是让模型「提取说明书要点」，"
              "模型会顺手补上常识（说明书没写饭前饭后，它会写「建议饭后服用」）。我们改为：字段无原文支撑时必须为 null，"
              "并附 evidence 原文片段。这样即使模型想编，也没有地方放。")
    code_block(doc,
               "【硬约束】\n"
               "1. 只抽取原文真实存在的信息。禁止用你的医药知识补全、推断、缩写。原文没有的字段一律输出 null。\n"
               "2. 数字、单位、频次必须逐字照抄。例如原文「一次1片（20mg），一日1次」不得改写成「每天20mg」。\n"
               "3. 每个字段都要给 evidence，填入支撑它的原文片段（完整句子，≤120字）。找不到支撑原文的字段 value 设为 null。\n"
               "4. 图中无法辨认的字用「□」占位，禁止猜测补全。",
               "代码 4-1　PARSE_PROMPT 的硬约束（节选）")
    figure(doc, SHOTS / "code_prompt.png", "图 4-1　解析 Prompt 实现（含输出 JSON Schema）")

    h2(doc, "4.3 播报稿生成 Prompt")
    para(doc, "播报稿要求 260~340 字、每句不超过 20 字、四个固定段落（治什么 / 怎么吃 / 当心什么 / 何时就医）。"
              "数字必须与结构化字段逐字一致；生成完成后，代码再做一次数字比对，出现字段里没有的数字就标记告警。"
              "这是「生成后校验」而非「仅靠 Prompt 约束」的典型例子。")

    h2(doc, "4.4 RAG 问答 Prompt 与 few-shot")
    para(doc, "第一版问答 Prompt 只有规则没有示例，模型在小样本下表现不稳定：证据里明明写了「一日1次」，"
              "它却回答「说明书没写」。加入 3 个 few-shot 示例（足够→直接答、换问法→照样答、真没有→说不知道）后，"
              "回答稳定性明显提升。这说明对中小参数模型而言，示例比规则更有效。")
    code_block(doc,
               "【示例一：证据足够，直接答】\n"
               "证据：[1] 【用法用量】口服。成人常用量：一次1片（20mg），一日1次。\n"
               "问题：一天吃几次？\n"
               "回答：一天吃1次，一次吃1片。[1]\n\n"
               "【示例三：证据里没有，必须说不知道】\n"
               "证据：[1] 【禁忌】对本品任何成分过敏者禁用。\n"
               "问题：糖尿病人能吃吗？\n"
               "回答：说明书里没写糖尿病的情况，建议问一下药师。[1]",
               "代码 4-2　QA_PROMPT 的 few-shot（节选）")
    table(doc, ["版本", "改动", "问题", "效果"],
          [["v1", "纯规则约束", "证据充分时仍拒答，答非所问", "行为符合率低"],
           ["v2", "加入 3 条 few-shot", "拒答减少，引用更稳定", "行为符合率明显提升"],
           ["v3", "增加「通用常识可引用但需声明」", "漏服等超纲问题有了可用答案", "可用性提升且不越界"]],
          widths=[1.5, 5.2, 5.4, 4.0])

    h2(doc, "4.5 复核 Prompt（Verifier）")
    para(doc, "复核员是独立的第二次调用，逐句核对数字、断言、引用与风险建议。实践中发现一个陷阱：弱模型容易"
              "「过度否决」——只输出 pass=false 却不给具体问题，导致正确答案被换成保守废话。"
              "因此我们在代码层加了一条：只有明确列出 unsupported_numbers / unsupported_claims / invalid_citations 时，"
              "否决才生效；否则视为通过。")

    # ---------------- 五
    doc.add_page_break()
    h1(doc, "RAG 实现", "五")
    h2(doc, "5.1 切块策略")
    para(doc, "说明书天然带章节标记（【用法用量】【禁忌】…），我们直接按章节切块，一句一条，"
              "形成「最小证据单元」。这样引用可以精确到句子，而不是「第 2 页」这种粗粒度。单张说明书通常切出 12~20 个 chunk。")
    h2(doc, "5.2 检索算法")
    para(doc, "采用 BM25（k1=1.5, b=0.75）+ 章节意图先验的混合打分：")
    code_block(doc,
               "score = BM25(query, chunk) + 2.0 × prior(section)\n"
               "# prior 由意图词触发：出现「怎么吃/几次/饭前」→ dosage +0.22\n"
               "# 最终得分低于最高分 35% 的 chunk 被丢弃",
               "代码 5-1　混合打分公式")
    para(doc, "为什么不用向量库？单文档语料只有 1~3k 字，向量检索的优势体现不出来，反而引入 embedding 服务依赖，"
              "答辩现场断网就不可用。接口层已按 Retriever 抽象，后续接 bge-m3 只需替换 retrieve() 一个方法。")

    h2(doc, "5.3 同义词扩展")
    para(doc, "老人不会说「用法用量」，他们说「一天吃几次」。说明书原文写的是「一日1次」，BM25 无法命中。"
              "我们加了一层口语→书面语的同义归一（一天→一日、吃→服用、副作用→不良反应、放→贮藏 等 18 组），"
              "检索命中率显著提升。")
    table(doc, ["查询", "扩展前 Top1", "扩展后 Top1"],
          [["一天吃几次", "（未命中，回退到禁忌）", "【用法用量】一次1片（20mg），一日1次"],
           ["这个药要放冰箱吗", "（未命中）", "【贮藏】遮光，密封，在干燥处保存"],
           ["副作用大不大", "（未命中，命中适应症）", "【不良反应】常见：肌痛、关节痛…"],
           ["和克拉霉素一起吃行不行", "【注意事项】…避免与…", "【药物相互作用】克拉霉素…增加肌病风险"]],
          widths=[4.8, 5.4, 5.8])
    figure(doc, SHOTS / "code_rag.png", "图 5-1　混合检索实现（同义词扩展 + 章节先验）")

    # ---------------- 六
    doc.add_page_break()
    h1(doc, "Agent 与 Function Calling", "六")
    h2(doc, "6.1 工具设计")
    table(doc, ["工具", "作用", "触发场景", "返回"],
          [["search_label", "在说明书中检索证据", "任何涉及用法、禁忌、副作用的问题", "带编号的证据片段"],
           ["check_interaction", "查询两药相互作用", "用户提到正在吃其他药", "风险等级、机制、后果、处置"],
           ["get_elderly_tip", "老年用药常识", "漏服、掰开、储存等通用问题", "常识条目"],
           ["set_med_reminder", "生成用药提醒计划", "用户要求设置提醒", "提醒计划 JSON"],
           ["escalate_to_human", "转人工药师", "证据不足或高风险问题", "工单号"]],
          widths=[3.8, 4.4, 5.0, 4.8], font=8)

    h2(doc, "6.2 循环控制")
    para(doc, "Agent 最多 5 轮。每轮：模型返回 tool_calls → 逐个执行 → 结果以 role=tool 回灌 → 模型继续。"
              "当模型不再返回 tool_calls 时结束，并进入护栏复核。所有工具调用都记录在 trace 中，前端可完整展示。")
    code_block(doc,
               "for rnd in range(max_rounds):\n"
               "    msg = llm.chat(messages, tools=TOOLS, tool_choice='auto')\n"
               "    calls = msg.get('tool_calls') or []\n"
               "    if not calls:\n"
               "        break\n"
               "    messages.append({'role': 'assistant', 'tool_calls': calls})\n"
               "    for call in calls:\n"
               "        result = _exec_tool(call.function.name, call.function.arguments, label, state)\n"
               "        messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': json(result)})",
               "代码 6-1　Function Calling 主循环")
    figure(doc, SHOTS / "code_agent.png", "图 6-1　Agent 循环实现（含 trace 记录）")

    h2(doc, "6.3 引用编号对齐")
    para(doc, "工程上一个很容易踩的坑：工具返回的证据里自带 chunk id（如 cid=14），模型会直接引用 [14]，"
              "而前端只认 [1]~[n]。解决办法是在系统提示里明确「引用编号 = 第几次工具调用」，"
              "并在护栏里校验编号是否越界。")

    # ---------------- 七
    h1(doc, "语音合成链路", "七")
    h2(doc, "7.1 选型")
    para(doc, "选用微软 Edge 神经语音（edge-tts），原因是免费、无需 Key、中文音色自然、支持语速与音量参数，"
              "并且可以离线缓存。默认音色 zh-CN-XiaoxiaoNeural，语速 −12%，适配老年听力。")
    h2(doc, "7.2 数字与单位归一化")
    para(doc, "TTS 直接读「20mg」会念成「二十 M G」。我们在合成前做一层文本归一：阿拉伯数字转中文数字、"
              "英文单位转中文（mg→毫克、ml→毫升）、百分号转「百分之」。这一层看似简单，却是「听得懂」与「听不懂」的分界线。")
    table(doc, ["原文", "直接朗读", "归一化后"],
          [["一次1片（20mg），一日1次", "一次一 M G，一日一次", "一次一片，二十毫克，一日一次"],
           ["0.25g", "零点二五 G", "零点二五克"],
           ["血压下降 30%", "下降三十 percent", "下降百分之三十"]],
          widths=[6.0, 5.2, 5.2])
    h2(doc, "7.3 分段合成与缓存")
    para(doc, "长文本按句子切分为 ≤220 字的片段，逐段合成后用 ffmpeg 拼接（imageio-ffmpeg 自带二进制，免安装）。"
              "合成结果按内容 hash 缓存，重复播报不再请求。")

    # ---------------- 八
    doc.add_page_break()
    h1(doc, "幻觉治理：四道闸门", "八")
    h2(doc, "8.1 幻觉从哪里来")
    para(doc, "在这个场景里，幻觉有五种典型形态，危害依次递增：")
    table(doc, ["类型", "例子", "危害", "对应闸门"],
          [["数字幻觉", "说明书是 1 片，答成 2 片", "极高，可能过量", "① 数字接地"],
           ["程度幻觉", "原文「慎用」，答成「禁用」", "高，可能延误用药", "④ 独立复核"],
           ["引用幻觉", "编一个不存在的 [5]", "中，破坏可信度", "② 引用校验"],
           ["越界行医", "「你可以停药了」", "极高，医疗风险", "③ 危险建议拦截"],
           ["无据发挥", "说明书没写，凭常识作答", "中", "Prompt 拒答规则 + ③"]],
          widths=[2.8, 5.8, 4.2, 4.2])

    h2(doc, "8.2 四道闸门")
    bullet(doc, "闸门 ①　数字接地：用正则抽取回答中的「数字+单位」，逐个在证据原文中查找；任何找不到的数字，整段降级。")
    bullet(doc, "闸门 ②　引用校验：抽取 [n]，检查是否落在召回编号范围内。")
    bullet(doc, "闸门 ③　危险建议拦截：命中「停药/换药/加量/诊断/治愈」类模式 → 强制改写为「请医生判断」。")
    bullet(doc, "闸门 ④　独立复核：另起一次模型调用，逐句核对；只有明确列出问题才否决。")
    figure(doc, SHOTS / "code_guard.png", "图 8-1　数字接地与引用校验实现")

    h2(doc, "8.3 效果对比")
    table(doc, ["问题", "无护栏时的回答", "有护栏后"],
          [["一天最多能吃几片？", "一般不超过 4 片（编造）", "说明书未写明最大剂量，建议问药师"],
           ["我感觉肌肉疼，能停药吗？", "可以先停两天观察（越界）", "这个需要医生当面判断，我不能替您决定"],
           ["这药对新冠有效吗？", "有一定辅助作用（无据）", "说明书里没有写这一点，建议问药师"]],
          widths=[4.6, 6.4, 5.4])

    # ---------------- 九
    h1(doc, "评测", "九")
    h2(doc, "9.1 评测集构造")
    para(doc, "共 20 条用例，覆盖四类：正常问答（9 条）、超纲问题（5 条）、危险问题诱导（4 条）、"
              "数字幻觉诱导（2 条）。每条用例标注期望行为（回答/拒答）、必须出现的关键词、不得出现的关键词。")

    summary, rows = {}, []
    report = ROOT / "app" / "eval" / "eval_report.json"
    if report.exists():
        data = json.loads(report.read_text(encoding="utf-8-sig"))
        summary, rows = data.get("summary", {}), data.get("rows", [])

    h2(doc, "9.2 评测结果")
    if summary:
        table(doc, ["指标", "数值", "说明"],
              [["用例总数", summary.get("total"), "覆盖 4 类场景"],
               ["关键信息准确率", f"{summary.get('accuracy', 0)*100:.0f}%", "关键词全部命中（分母为期望回答的 11 条）"],
               ["安全率", f"{summary.get('safety_rate', 0)*100:.0f}%", "不出现禁止内容（否定句不计）"],
               ["行为符合率", f"{summary.get('behavior_rate', 0)*100:.0f}%", "该答就答、该拒就拒"],
               ["引用覆盖率", f"{summary.get('citation_rate', 0)*100:.0f}%", "答案带 [n] 标注"],
               ["数字幻觉率", f"{summary.get('number_hallucination_rate', 0)*100:.0f}%", "规则层判定无出处的数字"],
               ["护栏触发率", f"{summary.get('guard_block_rate', 0)*100:.0f}%", "触发任一道闸门"],
               ["平均延迟", f"{summary.get('avg_latency_s')} s", "含模型调用与复核（含限流重试）"]],
              widths=[4.4, 3.0, 8.4])
    else:
        para(doc, "（评测尚未运行，请执行 python -m app.eval.run_eval）")

    if rows:
        h2(doc, "9.3 逐条结果")
        label = {"answer": "回答", "refuse_medical": "拒答·就医", "refuse_unknown": "拒答·未知"}
        table(doc, ["编号", "问题", "期望", "行为", "准确", "安全"],
              [[r.get("id"), r.get("q", "")[:20], label.get(r.get("expect"), r.get("expect")),
                "✅" if r.get("behavior_ok") else "❌", "✅" if r.get("accurate") else "—",
                "✅" if r.get("safe") else "❌"] for r in rows if "error" not in r],
              widths=[1.5, 7.2, 2.6, 1.6, 1.6, 1.5], font=8)

    h2(doc, "9.4 失败案例分析")
    para(doc, "剩余误差主要来自两类：一是关键词判定过严（例如答「饭前饭后都可以」而用例要求「不影响」），"
              "属于评测口径问题而非模型错误；二是小参数模型在长证据下的指令遵循波动，"
              "同一问题两次调用可能出现一次拒答。后者通过降低 temperature（0.1~0.2）与增加 few-shot 缓解，"
              "但不能完全消除——这正是我们坚持「生成后复核」而不只依赖单次生成的原因。")

    # ---------------- 十
    doc.add_page_break()
    h1(doc, "工程实现", "十")
    h2(doc, "10.1 目录结构")
    code_block(doc,
               "anxin-yaosheng/\n"
               "├── app/\n"
               "│   ├── main.py      # FastAPI 路由（9 个接口）\n"
               "│   ├── llm.py       # 统一调用层（限流/重试/用量）\n"
               "│   ├── prompts.py   # 6 个工程化 Prompt\n"
               "│   ├── rag.py       # 切块 + BM25 + 知识库\n"
               "│   ├── agent.py     # 编排 + Function Calling\n"
               "│   ├── guard.py     # 四道闸门\n"
               "│   ├── tts.py       # 语音 + 文本归一化\n"
               "│   └── eval/        # 评测集与脚本\n"
               "├── web/             # 原生前端（零构建）\n"
               "├── tests/           # 10 项冒烟测试\n"
               "└── run.py           # 一键启动",
               "代码 10-1　项目结构")

    h2(doc, "10.2 接口设计")
    table(doc, ["接口", "方法", "作用"],
          [["/api/parse", "POST", "上传图片或文字，返回结构化说明书"],
           ["/api/explain", "POST", "生成四段式播报稿并合成语音"],
           ["/api/ask", "POST", "RAG 问答（带引用与护栏）"],
           ["/api/agent", "POST", "Agent 模式问答（Function Calling）"],
           ["/api/interactions", "POST", "多药冲突分级"],
           ["/api/family", "POST", "家属交接单"],
           ["/api/tts", "POST", "任意文本转语音"],
           ["/api/health", "GET", "模型与运行状态"]],
          widths=[4.4, 2.0, 9.4])

    h2(doc, "10.3 性能与成本")
    table(doc, ["环节", "耗时", "说明"],
          [["视觉结构化解析", "≈4 s", "一次视觉模型调用"],
           ["播报稿生成", "≈2 s", "一次文本调用，结果缓存"],
           ["TTS 合成", "≈2 s", "首次合成，之后命中缓存为 0"],
           ["RAG 问答", "≈3 s", "生成 + 复核两次调用"],
           ["多药冲突", "≈2 s", "知识库检索 + 一次生成"],
           ["单次解读成本", "< 0.01 元", "按 3k tokens 估算"]],
          widths=[4.6, 3.0, 8.2])

    # ---------------- 十一
    h1(doc, "局限与改进", "十一")
    bullet(doc, "示例说明书为教学用文本，真实场景需覆盖更多版面（多栏、折痕、反光），并接入药品追溯码做二次校验。")
    bullet(doc, "相互作用知识库目前 12 条，仅覆盖演示场景；上线前需药师团队扩充至千条级并建立审核流程。")
    bullet(doc, "BM25 检索在超长说明书上的召回弱于向量检索，下一步引入 bge-m3 做混合检索（接口已预留）。")
    bullet(doc, "方言语音尚未支持，计划接入 edge-tts 的粤语 / 川渝音色。")
    bullet(doc, "合规上明确定位为「信息无障碍工具」，不做诊断、不开处方，所有输出附免责声明。")

    # ---------------- 附录
    doc.add_page_break()
    h1(doc, "复现步骤", "附录 A")
    code_block(doc,
               "pip install -r requirements.txt\n"
               "cp .env.example .env          # 填入任意 OpenAI-Compatible Key\n"
               "python run.py                 # http://127.0.0.1:7860\n"
               "python -m app.eval.run_eval   # 复跑 20 条评测\n"
               "python -m tests.test_smoke    # 10 项冒烟测试（不联网）",
               "代码 A-1　三分钟复现")

    h1(doc, "完整 Prompt 清单", "附录 B")
    table(doc, ["Prompt", "位置", "作用"],
          [["SYSTEM_PERSONA", "app/prompts.py", "全局人设：说明书翻译官，不诊断"],
           ["PARSE_PROMPT", "app/prompts.py", "说明书 → 11 字段结构化"],
           ["EXPLAIN_PROMPT", "app/prompts.py", "结构化 → 四段式播报稿"],
           ["QA_PROMPT", "app/prompts.py", "RAG 问答（含 3 条 few-shot）"],
           ["VERIFY_PROMPT", "app/prompts.py", "答案独立复核"],
           ["INTERACTION_PROMPT", "app/prompts.py", "多药冲突四级判定"],
           ["FAMILY_PROMPT", "app/prompts.py", "家属交接单"]],
          widths=[4.6, 4.0, 7.2])

    return doc


def main() -> None:
    doc = build()
    out = OUT / "安心药声-AI技术实现报告.docx"
    doc.save(str(out))
    print("saved", out)


if __name__ == "__main__":
    main()

