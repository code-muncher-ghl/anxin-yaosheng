"""把 assets/*.html 的架构图/流程图渲染成 2x PNG，供 BP 与技术报告使用。

用法：python tools/render_diagrams.py
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
OUT = ASSETS / "shots"
OUT.mkdir(parents=True, exist_ok=True)


def launch(p):
    try:
        return p.chromium.launch(channel="msedge")
    except Exception:
        try:
            return p.chromium.launch(channel="chrome")
        except Exception:
            return p.chromium.launch()


def main() -> None:
    pages = {
        "diagram_arch.html": "diagram_arch.png",
        "diagram_flow.html": "diagram_flow.png",
    }
    with sync_playwright() as p:
        browser = launch(p)
        page = browser.new_page(viewport={"width": 1600, "height": 980}, device_scale_factor=2)
        for src, dst in pages.items():
            page.goto((ASSETS / src).as_uri())
            page.wait_for_timeout(600)
            page.screenshot(path=str(OUT / dst))
            print("saved", dst)
        browser.close()


if __name__ == "__main__":
    main()
