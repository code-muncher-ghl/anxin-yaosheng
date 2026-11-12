"""一键启动：python run.py

- 首次运行会检查依赖与大模型配置
- 默认端口 7860，可用环境变量 PORT 覆盖
"""
from __future__ import annotations

import os
import sys
import webbrowser
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def preflight() -> None:
    from app import config

    print("=" * 56)
    print(f" {config.APP_NAME} · {config.APP_SLOGAN}")
    print("=" * 56)
    print(f" 接口地址   : {config.LLM_BASE_URL}")
    print(f" 对话模型   : {config.LLM_MODEL}")
    print(f" 视觉模型   : {config.LLM_VISION_MODEL}")
    print(f" 校验模型   : {config.LLM_VERIFY_MODEL}")
    if not config.LLM_API_KEY:
        print("\n[!] 未检测到 LLM_API_KEY，页面可以打开，但识别/问答会失败。")
        print("    请复制 .env.example 为 .env 并填入 Key。\n")
    else:
        print(" Key        : 已配置（已脱敏）\n")


if __name__ == "__main__":
    preflight()
    port = int(os.getenv("PORT", "7860"))
    if os.getenv("OPEN_BROWSER", "0") == "1":
        webbrowser.open(f"http://127.0.0.1:{port}")
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=False, log_level="warning")
