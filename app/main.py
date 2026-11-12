"""安心药声 · API 服务

启动：python run.py   （默认 http://127.0.0.1:7860）
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import agent, config, prompts, tts
from .llm import LLMError, llm
from .rag import KB, Retriever

BASE = Path(__file__).resolve().parent.parent
WEB = BASE / "web"
SAMPLES = json.loads((BASE / "app" / "kb" / "samples.json").read_text(encoding="utf-8-sig"))["samples"]

app = FastAPI(title=config.APP_NAME, version="1.0.0")

# 内存态：演示用，重启即清空（生产应落库）
LABELS: dict[str, dict] = {}
SCRIPTS: dict[str, dict] = {}
ASK_CACHE: dict[tuple, dict] = {}
HISTORY: list[dict] = []


def _store(label: dict) -> dict:
    LABELS[label["id"]] = label
    return label


def _get(label_id: str) -> dict:
    if label_id not in LABELS:
        raise HTTPException(404, "说明书不存在，请先上传或选择示例")
    return LABELS[label_id]


@app.get("/api/health")
def health():
    return {
        "app": config.APP_NAME,
        "llm_configured": llm.configured,
        "base_url": config.LLM_BASE_URL,
        "model": config.LLM_MODEL,
        "vision_model": config.LLM_VISION_MODEL,
        "labels_in_memory": len(LABELS),
        "usage": llm.cost_report(),
    }


@app.get("/api/samples")
def samples():
    return [{"id": s["id"], "title": s["title"], "subtitle": s["subtitle"]} for s in SAMPLES]


@app.post("/api/demo/{sample_id}")
def load_demo(sample_id: str):
    sample = next((s for s in SAMPLES if s["id"] == sample_id), None)
    if not sample:
        raise HTTPException(404, "示例不存在")
    data = dict(sample["structured"])
    data["id"] = agent.new_id()
    data["raw"] = sample["structured"]
    data["evidence"] = sample["structured"].get("evidence", {})
    data["confidence"] = sample["structured"].get("confidence", 0.9)
    data["_meta"] = {"source": "demo", "ms": 0}
    _store(data)
    return {"label": data}


@app.post("/api/parse")
async def parse(file: UploadFile | None = File(None), text: str = Form("")):
    if file is not None:
        raw = await file.read()
        if not raw:
            raise HTTPException(400, "图片为空")
        suffix = Path(file.filename or "x.jpg").suffix or ".jpg"
        (config.UPLOAD_DIR / f"{int(time.time())}{suffix}").write_bytes(raw)
        mime = file.content_type or "image/jpeg"
        data = agent.parse_from_image(raw, mime)
    elif text.strip():
        data = agent.parse_from_text(text)
    else:
        raise HTTPException(400, "请上传说明书照片或粘贴文字")
    _store(data)
    return {"label": data}


@app.post("/api/explain")
def explain(payload: dict):
    label = _get(payload.get("label_id", ""))
    if label["id"] in SCRIPTS and not payload.get("force"):
        return SCRIPTS[label["id"]]
    script = agent.make_script(label)
    audio = tts.synthesize(
        "。" .join([f"{s['title']}。{s['text']}" for s in script["segments"]]) + "。" + script["safety_note"]
    )
    result = {"label_id": label["id"], "script": script, "audio": audio, "disclaimer": config.DISCLAIMER}
    SCRIPTS[label["id"]] = result
    return result


@app.post("/api/ask")
def ask(payload: dict):
    label = _get(payload.get("label_id", ""))
    question = (payload.get("question") or "").strip()
    if not question:
        raise HTTPException(400, "问题不能为空")
    cache_key = (label["id"], question)
    if cache_key in ASK_CACHE:
        return ASK_CACHE[cache_key]
    result = agent.answer_question(label, question)
    ASK_CACHE[cache_key] = result
    HISTORY.append({"type": "ask", "q": question, "a": result["answer"]})
    return result


@app.post("/api/agent")
def run_agent_endpoint(payload: dict):
    label = _get(payload.get("label_id", ""))
    question = (payload.get("question") or "").strip()
    if not question:
        raise HTTPException(400, "问题不能为空")
    return agent.run_agent(label, question)


@app.post("/api/interactions")
def interactions(payload: dict):
    ids = payload.get("label_ids") or []
    labels = [_get(i) for i in ids]
    if len(labels) < 2:
        raise HTTPException(400, "至少需要两种药")
    return agent.analyze_interactions(labels)


@app.post("/api/family")
def family(payload: dict):
    ids = payload.get("label_ids") or []
    labels = [_get(i) for i in ids]
    if not labels:
        raise HTTPException(400, "请先添加药品")
    return agent.family_summary(labels, payload.get("extra", ""))


@app.post("/api/tts")
def tts_endpoint(payload: dict):
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "文本为空")
    return tts.synthesize(text, payload.get("voice"), payload.get("rate"))


@app.get("/api/kb")
def kb():
    return {"interactions": KB["entries"], "elderly": KB["elderly_precautions"]}


@app.get("/api/usage")
def usage():
    return llm.cost_report()


@app.post("/api/reset")
def reset():
    LABELS.clear()
    SCRIPTS.clear()
    ASK_CACHE.clear()
    HISTORY.clear()
    return {"ok": True}


@app.exception_handler(LLMError)
def llm_error_handler(request: Request, exc: LLMError):
    return JSONResponse(status_code=502, content={"error": "llm_error", "detail": str(exc)})


app.mount("/audio", StaticFiles(directory=str(config.AUDIO_DIR)), name="audio")
app.mount("/", StaticFiles(directory=str(WEB), html=True), name="web")

