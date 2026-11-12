"""安心药声 · 全局配置

所有大模型调用统一走 OpenAI-Compatible 协议，因此同一个适配层可以接
火山方舟(豆包) / DeepSeek / 智谱 GLM / 阿里百炼(千帆) / 硅基流动 / 本地 Ollama。
切换供应商只需要改 .env，不用改一行代码。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ---------- 大模型 ----------
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "doubao-seed-1-6-flash-250715")
# 视觉模型负责"看说明书"，没有单独配置时复用主模型
LLM_VISION_MODEL = os.getenv("LLM_VISION_MODEL", "") or LLM_MODEL
# 校验模型负责"复核答案"，留空则复用主模型
LLM_VERIFY_MODEL = os.getenv("LLM_VERIFY_MODEL", "") or LLM_MODEL

LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "90"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
# 用于成本测算：每百万 token 的单价（元），仅用于报告展示
PRICE_IN = float(os.getenv("PRICE_IN_PER_M", "0.8"))
PRICE_OUT = float(os.getenv("PRICE_OUT_PER_M", "2.0"))

# ---------- 存储 / 产物 ----------
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
AUDIO_DIR = DATA_DIR / "audio"
for _d in (DATA_DIR, UPLOAD_DIR, AUDIO_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------- 语音 ----------
TTS_VOICE = os.getenv("TTS_VOICE", "zh-CN-XiaoxiaoNeural")
TTS_RATE = os.getenv("TTS_RATE", "-12%")   # 慢一点，适配老年听力
TTS_VOLUME = os.getenv("TTS_VOLUME", "+0%")

# ---------- 安全策略 ----------
# 证据不足时直接拒答的检索分阈值（BM25 归一化后）
MIN_EVIDENCE_SCORE = float(os.getenv("MIN_EVIDENCE_SCORE", "0.12"))
# 强制医疗免责声明
DISCLAIMER = (
    "本解读仅用于帮助理解说明书原文，不能替代医生或药师的诊断与用药指导。"
    "如出现不适或需要调整用药，请立即咨询医生或药师。"
)

APP_NAME = "安心药声"
APP_SLOGAN = "拍一下说明书，听见安全用药"
