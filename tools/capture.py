"""用 Playwright 抓取真实界面截图（用于 BP / 技术报告 / 演示视频）

前置：python run.py 已在 7860 端口运行
用法：python tools/capture.py
"""
from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "shots"
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:7860"


def shot(page, name: str, wait: float = 2.6) -> None:
    time.sleep(wait)
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
    print("saved", name)


def main() -> None:
    with sync_playwright() as p:
        # 优先用系统已安装的 Edge/Chrome，免去下载 Chromium（国内网络更稳）
        try:
            browser = p.chromium.launch(channel="msedge")
        except Exception:
            try:
                browser = p.chromium.launch(channel="chrome")
            except Exception:
                browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
        page.goto(BASE, wait_until="networkidle")
        time.sleep(1.2)
        shot(page, "01_home", 0.4)

        # 解析结果
        page.click('#sampleChips .chip[data-id="lipitor"]')
        page.wait_for_selector("#labelBody:not(.hidden)", timeout=20000)
        shot(page, "02_parse", 1.0)

        # 语音播报
        page.click("#btnExplain")
        page.wait_for_selector("#playerCard:not(.hidden)", timeout=180000)
        page.wait_for_function("document.querySelector('#audio').src.length > 0", timeout=60000)
        shot(page, "03_playback", 1.5)
        page.eval_on_selector("#audio", "el => { el.currentTime = 6; el.play(); }")
        time.sleep(1.2)
        shot(page, "04_playback_playing", 0.2)
        page.eval_on_selector("#audio", "el => el.pause()")

        # 用药问答
        page.click(".tab[data-tab='ask']")
        page.fill("#askInput", "这个药饭前吃还是饭后吃？")
        page.click("#btnAsk")
        page.wait_for_function("document.querySelectorAll('.msg.bot').length >= 1 && !document.querySelector('.msg.bot .loading')", timeout=180000)
        shot(page, "05_qa", 1.0)

        # Agent 模式
        page.check("#agentMode")
        page.fill("#askInput", "我同时在吃克拉霉素，这两个药能一起吃吗？")
        page.click("#btnAsk")
        page.wait_for_function("document.querySelectorAll('.msg.bot').length >= 2 && !document.querySelector('.msg.bot .loading')", timeout=240000)
        shot(page, "06_agent", 1.2)

        # 多药检查
        page.click(".tab[data-tab='mix']")
        time.sleep(0.4)
        shot(page, "07_basket", 0.4)
        page.click("#btnMix")
        page.wait_for_selector("#mixResult:not(.hidden)", timeout=240000)
        shot(page, "08_mix", 1.0)

        # 家属交接单
        page.click(".tab[data-tab='family']")
        page.click("#btnFamily")
        page.wait_for_selector(".fam-card", timeout=180000)
        shot(page, "09_family", 1.0)

        browser.close()
        print("done ->", OUT)


if __name__ == "__main__":
    main()
