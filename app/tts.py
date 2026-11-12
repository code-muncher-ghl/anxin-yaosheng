"""语音合成：edge-tts（微软神经语音，免费、无需 Key、支持方言与语速调节）

老年友好策略：
- 默认 zh-CN-XiaoxiaoNeural，语速 -12%，音量 +0%；
- 长文本按段落切分，逐段合成再拼接，避免单次请求过长导致截断；
- 结果按内容 hash 缓存，重复播报不重复请求。
"""
from __future__ import annotations

import asyncio
import hashlib
import re

import edge_tts

from . import config

# ------------------------------------------------------------------ 文本归一化
# TTS 直接读 "20mg" 会念成 "二十 M G"，必须转成中文数字与中文单位
_DIGITS = "零一二三四五六七八九"
_UNITS = ["", "十", "百", "千", "万"]


def _num2cn(n: int) -> str:
    if n == 0:
        return "零"
    s = str(n)
    out, zero = [], False
    length = len(s)
    for i, ch in enumerate(s):
        d = int(ch)
        pos = length - i - 1
        if d == 0:
            zero = True
            continue
        if zero and out:
            out.append("零")
        zero = False
        out.append(_DIGITS[d] + _UNITS[pos])
    res = "".join(out)
    res = res.replace("一十", "十")
    return res


def _cn_number(token: str) -> str:
    if "." in token:
        a, b = token.split(".", 1)
        return _num2cn(int(a)) + "点" + "".join(_DIGITS[int(x)] for x in b)
    return _num2cn(int(token))


UNIT_MAP = [
    (r"(?<=\d)\s*(mg|毫克)", "毫克"),
    (r"(?<=\d)\s*(μg|ug|微克)", "微克"),
    (r"(?<=\d)\s*(ml|mL|毫升)", "毫升"),
    (r"(?<=\d)\s*(g|克)(?![a-zA-Z])", "克"),
    (r"(?<=\d)\s*(IU|iu|单位)", "单位"),
]


def normalize_for_tts(text: str) -> str:
    """把阿拉伯数字、英文单位、符号转成适合朗读的中文。"""
    if not text:
        return ""
    out = text
    for pattern, repl in UNIT_MAP:
        out = re.sub(pattern, repl, out)
    out = re.sub(r"(\d+(?:\.\d+)?)\s*%", lambda m: "百分之" + _cn_number(m.group(1)), out)
    out = re.sub(r"\d+(?:\.\d+)?", lambda m: _cn_number(m.group(0)), out)
    # 常见符号
    out = out.replace("①②③④", "。").replace("+", "加").replace("~", "到").replace("～", "到")
    out = re.sub(r"[【】\[\]]", "", out)
    return out


def _hash(text: str, voice: str, rate: str) -> str:
    return hashlib.md5(f"{text}|{voice}|{rate}".encode()).hexdigest()[:16]


def _split(text: str, limit: int = 220) -> list[str]:
    parts = re.split(r"(?<=[。！？；\n])", text)
    out, buf = [], ""
    for p in parts:
        if len(buf) + len(p) > limit and buf:
            out.append(buf)
            buf = p
        else:
            buf += p
    if buf.strip():
        out.append(buf)
    return [p.strip() for p in out if p.strip()]


async def _synth(text: str, path: str, voice: str, rate: str) -> None:
    com = edge_tts.Communicate(text, voice=voice, rate=rate, volume=config.TTS_VOLUME)
    await com.save(path)


def synthesize(text: str, voice: str | None = None, rate: str | None = None) -> dict:
    voice = voice or config.TTS_VOICE
    rate = rate or config.TTS_RATE
    spoken = normalize_for_tts(text)
    key = _hash(spoken, voice, rate)
    mp3 = config.AUDIO_DIR / f"{key}.mp3"
    if mp3.exists() and mp3.stat().st_size > 0:
        return {"file": mp3.name, "url": f"/audio/{mp3.name}", "cached": True, "chars": len(spoken)}

    chunks = _split(spoken)
    tmp_files = []
    for i, piece in enumerate(chunks):
        p = config.AUDIO_DIR / f"{key}_{i}.mp3"
        asyncio.run(_synth(piece, str(p), voice, rate))
        tmp_files.append(p)

    if len(tmp_files) == 1:
        tmp_files[0].rename(mp3)
    else:
        # 用 ffmpeg 拼接（imageio-ffmpeg 自带二进制，免安装）
        try:
            import subprocess

            import imageio_ffmpeg

            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            lst = config.AUDIO_DIR / f"{key}.txt"
            lst.write_text("\n".join(f"file '{p}'" for p in tmp_files), encoding="utf-8")
            subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(mp3)],
                           check=True, capture_output=True)
        except Exception:
            tmp_files[0].rename(mp3)
    for p in tmp_files:
        if p.exists() and p != mp3:
            p.unlink(missing_ok=True)

    return {"file": mp3.name, "url": f"/audio/{mp3.name}", "cached": False, "chars": len(text)}
