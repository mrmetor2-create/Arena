"""Шаг 1. Расшифровка речи с таймингом каждого слова (faster-whisper).

    python tools/transcribe.py ролик
    python tools/transcribe.py ролик --prompt "Claude Code, Remotion, нейросеть"   # подсказка для терминов
    python tools/transcribe.py --download-only                                      # заранее скачать модель

Результат в work/<ролик>/:
    transcript.json — слова с временем (сюда вносятся исправления)
    transcript.txt  — текст для проверки человеком; «слово(?)» = Whisper не уверен
"""
from __future__ import annotations

import argparse

import subprocess

import numpy as np

from common import die, need, resolve_work, save_json, ts

DEFAULT_MODEL = "large-v3-turbo"
QUOTES = "«»\"„“”'"
SENTENCE_END = (".", "!", "?", "…")


def load_model(name: str, device: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        die("не установлен faster-whisper. Запусти install.ps1 (или: .venv\\Scripts\\python -m pip install -r tools\\requirements.txt)")

    attempts = []
    if device in ("auto", "cuda"):
        attempts.append(("cuda", "float16"))
    if device in ("auto", "cpu"):
        attempts.append(("cpu", "int8"))
    last = None
    for dev, ctype in attempts:
        try:
            model = WhisperModel(name, device=dev, compute_type=ctype)
            print(f"Модель {name} на {dev} ({ctype})")
            return model
        except Exception as e:  # нет CUDA/cuDNN — падаем на CPU
            last = e
    die(f"не удалось загрузить модель: {last}")


def decode_audio(path) -> np.ndarray:
    """Звук через ffmpeg: 16 кГц моно float32 (не зависим от версии PyAV)."""
    need("ffmpeg")
    res = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(path),
                          "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True)
    if res.returncode != 0:
        die(res.stderr.decode("utf-8", "replace")[-1500:])
    return np.frombuffer(res.stdout, dtype=np.float32)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", nargs="?", help="имя ролика (папка в work/) или путь к исходнику")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="large-v3-turbo (по умолчанию), large-v3, medium, small")
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    ap.add_argument("--prompt", default="", help="термины и имена, которые должны быть написаны правильно")
    ap.add_argument("--download-only", action="store_true")
    ap.add_argument("--low-prob", type=float, default=0.5, help="ниже этой уверенности слово помечается (?)")
    args = ap.parse_args()

    model = load_model(args.model, args.device)
    if args.download_only:
        print("Модель скачана.")
        return
    if not args.video:
        die("укажи ролик")

    d = resolve_work(args.video)
    proxy = d / "proxy.mp4"
    if not proxy.is_file():
        die(f"нет {proxy}. Сначала prepare.py")

    print(f"Расшифровываю {proxy} ...")
    segments, info = model.transcribe(
        decode_audio(proxy),
        language=args.lang or None,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
        initial_prompt=args.prompt or None,
        condition_on_previous_text=False,
        beam_size=5,
    )

    words, segs, seg_lists = [], [], []
    for s in segments:
        seg_words = []
        for w in s.words or []:
            text = "".join(ch for ch in w.word if ch not in QUOTES).strip().lstrip("-").strip()
            if not text or not any(ch.isalnum() for ch in text):
                continue
            item = {"i": len(words), "text": text, "start": round(w.start, 3), "end": round(w.end, 3), "prob": round(w.probability, 3)}
            words.append(item)
            seg_words.append(item)
        if seg_words:
            seg_lists.append(seg_words)
            segs.append({"start": seg_words[0]["start"], "end": seg_words[-1]["end"], "text": " ".join(x["text"] for x in seg_words)})
        print(f"  [{ts(s.start)}] {s.text.strip()}")

    if not words:
        die("речь не найдена")

    save_json(d / "transcript.json", {"language": info.language, "duration": info.duration, "model": args.model, "words": words, "segments": segs})

    # строки для человека: по предложениям, не длиннее 14 слов
    lines, cur = [], []
    for k, w in enumerate(words):
        cur.append(w)
        nxt = words[k + 1] if k + 1 < len(words) else None
        if nxt is None or w["text"].endswith(SENTENCE_END) or len(cur) >= 14 or nxt["start"] - w["end"] > 1.0:
            text = " ".join(x["text"] + ("(?)" if x["prob"] < args.low_prob else "") for x in cur)
            lines.append(f"[{ts(cur[0]['start'])}–{ts(cur[-1]['end'])}] {text}")
            cur = []
    (d / "transcript.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    unsure = sum(1 for w in words if w["prob"] < args.low_prob)
    print(f"\nГотово: {len(words)} слов, неуверенных: {unsure}. Проверь {d / 'transcript.txt'}")
    print(f"Дальше: python tools/cutlist.py {d.name}")


if __name__ == "__main__":
    main()
