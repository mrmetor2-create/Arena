"""Шаг 3. Режет рабочую копию по cuts.json (только склейки с enabled: true).

    python tools/apply_cuts.py ролик

Результат в work/<ролик>/:
    cut.mp4    — ролик без пауз и дублей
    words.json — слова с новым временем (для субтитров)
    keeps.json — какие куски исходника остались и где они на новой шкале
Исходник и proxy.mp4 не трогает.
"""
from __future__ import annotations

import argparse

from common import FPS, die, ffmpeg_major, load_json, need, resolve_work, run, save_json, snap

MIN_KEEP = 0.10  # куски короче — выбрасываем
FADE = 0.012     # микрофейд звука на стыке, чтобы не щелкало


def keep_ranges(duration: float, cuts: list[dict]) -> list[tuple[float, float]]:
    spans = sorted((c["start"], c["end"]) for c in cuts if c.get("enabled", True))
    merged: list[list[float]] = []
    for s, e in spans:
        if merged and s <= merged[-1][1] + 1e-6:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    keeps, t = [], 0.0
    for s, e in merged:
        if s > t:
            keeps.append((t, s))
        t = max(t, e)
    if t < duration:
        keeps.append((t, duration))
    # к кадровой сетке: тогда длины видео и звука совпадают и рассинхрона нет
    out = []
    for s, e in keeps:
        s, e = snap(s), snap(e)
        if e - s >= MIN_KEEP:
            out.append((s, e))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--crf", type=int, default=17)
    args = ap.parse_args()

    need("ffmpeg")
    d = resolve_work(args.video)
    meta = load_json(d / "meta.json")
    cuts = load_json(d / "cuts.json")["cuts"]
    tr = load_json(d / "transcript.json")
    duration = snap(float(meta["duration"]))

    keeps = keep_ranges(duration, cuts)
    if not keeps:
        die("после склеек ничего не осталось — проверь cuts.json")

    parts, labels = [], []
    for k, (s, e) in enumerate(keeps):
        ln = e - s
        parts.append(f"[0:v]trim=start={s:.6f}:end={e:.6f},setpts=PTS-STARTPTS[v{k}]")
        parts.append(
            f"[0:a]atrim=start={s:.6f}:end={e:.6f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d={FADE},afade=t=out:st={max(0, ln - FADE):.6f}:d={FADE}[a{k}]"
        )
        labels.append(f"[v{k}][a{k}]")
    parts.append(f"{''.join(labels)}concat=n={len(keeps)}:v=1:a=1[v][a]")
    graph = ";\n".join(parts)

    script = d / "cuts_filter.txt"
    script.write_text(graph, encoding="utf-8")
    graph_arg = ["-/filter_complex", str(script)] if ffmpeg_major() >= 7 else ["-filter_complex_script", str(script)]

    out = d / "cut.mp4"
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(d / "proxy.mp4"), *graph_arg,
           "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
           "-pix_fmt", "yuv420p", "-r", str(FPS), "-fps_mode", "cfr",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(out)]
    print(f"Режу: {len(keeps)} кусков ...")
    run(cmd)

    # пересчет времени слов на новую шкалу
    table, offset = [], 0.0
    for s, e in keeps:
        table.append({"src_start": s, "src_end": e, "start": round(offset, 3), "end": round(offset + e - s, 3)})
        offset += e - s
    new_words = []
    for w in tr["words"]:
        mid = (w["start"] + w["end"]) / 2
        for k in table:
            if k["src_start"] <= mid < k["src_end"]:
                st = max(w["start"], k["src_start"]) - k["src_start"] + k["start"]
                en = min(w["end"], k["src_end"]) - k["src_start"] + k["start"]
                new_words.append({"text": w["text"], "start": round(st, 3), "end": round(max(en, st + 0.05), 3)})
                break
    save_json(d / "keeps.json", {"total": round(offset, 3), "keeps": table})
    save_json(d / "words.json", {"duration": round(offset, 3), "words": new_words})
    print(f"Готово: {out} ({offset:.1f} с, было {duration:.1f} с). Слов в субтитрах: {len(new_words)}")
    print(f"Дальше: python tools/build_project.py {d.name}")


if __name__ == "__main__":
    main()
