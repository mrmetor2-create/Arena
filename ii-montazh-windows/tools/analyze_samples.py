"""Разбор роликов-образцов для памятки стиля (style.md / style.json).

    python tools/analyze_samples.py                 # все ролики из samples/
    python tools/analyze_samples.py --words         # плюс темп речи (слов в минуту) через Whisper small

Результат в work/_samples/:
    <ролик>_sheet.jpg — контактный лист: кадр каждую секунду (смотреть шрифт, цвета, место текста, зумы)
    summary.md        — длина, средняя длина плана, склеек в секунду, громкость
Claude не слышит музыку и звуки — громкость и темп здесь только цифрами.
"""
from __future__ import annotations

import argparse
import re

from common import ROOT, WORK, die, duration_of, ffprobe, need, run, video_stream

EXT = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}


def scene_times(path, threshold: float) -> list[float]:
    res = run(["ffmpeg", "-hide_banner", "-i", str(path), "-vf", f"select='gt(scene,{threshold})',showinfo",
               "-an", "-f", "null", "-"], capture=True)
    return [float(x) for x in re.findall(r"pts_time:([\d.]+)", res.stderr)]


def loudness(path) -> str:
    res = run(["ffmpeg", "-hide_banner", "-i", str(path), "-vn", "-af", "ebur128", "-f", "null", "-"], capture=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", res.stderr)
    return f"{m[-1]} LUFS" if m else "нет звука"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.27, help="чувствительность поиска склеек")
    ap.add_argument("--words", action="store_true")
    args = ap.parse_args()
    need("ffmpeg")

    files = sorted(p for p in (ROOT / "samples").iterdir() if p.suffix.lower() in EXT)
    if not files:
        die("в samples/ нет роликов. Положи 4–5 образцов или скачай: yt-dlp -o \"samples/%(id)s.%(ext)s\" <ссылка>")
    out = WORK / "_samples"
    out.mkdir(parents=True, exist_ok=True)

    model = None
    if args.words:
        from faster_whisper import WhisperModel
        model = WhisperModel("small", device="cpu", compute_type="int8")

    rows = []
    for f in files:
        info = ffprobe(f)
        dur = duration_of(info)
        v = video_stream(info) or {}
        cuts = scene_times(f, args.threshold)
        shots = len(cuts) + 1
        n = min(30, max(6, int(dur)))
        cols = 6
        rows_n = (n + cols - 1) // cols
        sheet = out / f"{f.stem}_sheet.jpg"
        run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(f),
             "-vf", f"fps={n}/{max(dur, 1):.3f},scale=240:-2,tile={cols}x{rows_n}:padding=6:color=white",
             "-frames:v", "1", "-q:v", "3", str(sheet)])
        wpm = ""
        if model:
            segs, _ = model.transcribe(str(f), language="ru", vad_filter=True)
            count = sum(len(s.text.split()) for s in segs)
            wpm = f"{count / max(dur, 1) * 60:.0f}"
        rows.append((f.name, dur, f"{v.get('width')}x{v.get('height')}", shots, dur / shots, shots / max(dur, 1),
                     loudness(f), wpm, sheet.name))
        print(f"  {f.name}: {dur:.1f} с, планов {shots}, средний план {dur / shots:.1f} с")

    lines = ["# Разбор образцов", "",
             "| Ролик | Длина | Размер | Планов | Средний план | Склеек/с | Громкость | Слов/мин | Лист |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r[0]} | {r[1]:.1f} с | {r[2]} | {r[3]} | {r[4]:.1f} с | {r[5]:.2f} | {r[6]} | {r[7] or '—'} | {r[8]} |")
    lines += ["", "Склейки найдены по смене картинки: зумы и резкие движения тоже считаются, это ориентир, а не точное число."]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Готово: {out / 'summary.md'} и контактные листы *_sheet.jpg")


if __name__ == "__main__":
    main()
