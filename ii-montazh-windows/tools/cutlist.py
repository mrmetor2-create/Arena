"""Шаг 2. Список склеек: паузы, слова-паразиты, повторы слов и дубли фраз.

    python tools/cutlist.py ролик
    python tools/cutlist.py ролик --max-gap 0.5 --no-retakes

Результат в work/<ролик>/:
    cuts.json — склейки (поле enabled можно менять: true = вырезать)
    cuts.md   — таблица для проверки человеком

Ничего не режет. Резать будет apply_cuts.py после «да».
"""
from __future__ import annotations

import argparse

from common import load_json, norm, resolve_work, save_json, ts

FILLERS = {"э", "ээ", "эээ", "эм", "эмм", "эм-м", "ммм", "мм", "м", "хм", "а-а", "аа", "ааа",
           "m", "mm", "mmm", "hm", "hmm", "uh", "um", "em"}


def context(words, i0, i1, pad=3):
    left = " ".join(w["text"] for w in words[max(0, i0 - pad):i0])
    mid = " ".join(w["text"] for w in words[i0:i1 + 1])
    right = " ".join(w["text"] for w in words[i1 + 1:i1 + 1 + pad])
    return f"…{left} [{mid}] {right}…".replace("  ", " ")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--max-gap", type=float, default=0.35, help="паузы длиннее (с) вырезаются")
    ap.add_argument("--pad-before", type=float, default=0.08, help="запас перед словом (с)")
    ap.add_argument("--pad-after", type=float, default=0.15, help="запас после слова (с)")
    ap.add_argument("--no-fillers", action="store_true")
    ap.add_argument("--no-retakes", action="store_true")
    ap.add_argument("--retake-window", type=float, default=12.0, help="в пределах скольких секунд искать повтор фразы")
    args = ap.parse_args()

    d = resolve_work(args.video)
    tr = load_json(d / "transcript.json")
    words = tr["words"]
    meta = load_json(d / "meta.json")
    dur = float(meta["duration"])

    cuts = []

    def add(start, end, kind, reason, text, enabled=True, check=False):
        start, end = max(0.0, start), min(dur, end)
        if end - start >= 0.05:
            cuts.append({"start": round(start, 3), "end": round(end, 3), "kind": kind, "reason": reason,
                         "text": text, "enabled": enabled, "check": check})

    # 1) тишина в начале, в конце и паузы между словами
    add(0, words[0]["start"] - args.pad_before, "pause", "тишина в начале", "")
    for a, b in zip(words, words[1:]):
        gap = b["start"] - a["end"]
        if gap > args.max_gap:
            add(a["end"] + args.pad_after, b["start"] - args.pad_before, "pause", f"пауза {gap:.1f} с",
                f"{a['text']} … {b['text']}")
    add(words[-1]["end"] + args.pad_after + 0.2, dur, "pause", "тишина в конце", "")

    n = [norm(w["text"]) for w in words]

    # 2) слова-паразиты
    if not args.no_fillers:
        for i, w in enumerate(words):
            if n[i] in FILLERS:
                add(w["start"] - 0.02, w["end"] + 0.02, "filler", "слово-паразит", context(words, i, i))

    # 3) заикание: одно и то же слово два раза подряд («я я», «это это»)
    for i in range(len(words) - 1):
        if n[i] and n[i] == n[i + 1] and len(n[i]) <= 12 and words[i + 1]["start"] - words[i]["end"] < 1.0:
            add(words[i]["start"] - 0.02, words[i + 1]["start"] - 0.02, "stutter", "повтор слова", context(words, i, i))

    # 4) дубль: начало фразы повторяется заново — оставляем последнюю попытку
    if not args.no_retakes:
        k = 3
        i = 0
        while i < len(words) - k:
            gram = n[i:i + k]
            if all(gram):
                for j in range(i + 2, len(words) - k + 1):
                    if words[j]["start"] - words[i]["start"] > args.retake_window:
                        break
                    if n[j:j + k] == gram:
                        add(words[i]["start"] - 0.03, words[j]["start"] - args.pad_before, "retake",
                            f"дубль: фраза начата заново на {ts(words[j]['start'])}",
                            context(words, i, j - 1, pad=2), enabled=True, check=True)
                        i = j - 1
                        break
            i += 1

    cuts.sort(key=lambda c: c["start"])
    for idx, c in enumerate(cuts, 1):
        c["id"] = idx

    removed = sum(c["end"] - c["start"] for c in cuts if c["enabled"])
    save_json(d / "cuts.json", {"settings": vars(args), "duration": dur, "cuts": cuts})

    lines = [f"# Склейки: {d.name}", "",
             f"Длина исходника {ts(dur)}, вырезается примерно {removed:.1f} с, останется около {ts(dur - removed)}.", "",
             "| № | Время | Длина | Что | Текст | Резать |", "|---|---|---|---|---|---|"]
    for c in cuts:
        flag = "да" + (" — ПРОВЕРЬ" if c["check"] else "") if c["enabled"] else "нет"
        text = c["text"].replace("|", "/")
        lines.append(f"| {c['id']} | {ts(c['start'])}–{ts(c['end'])} | {c['end'] - c['start']:.2f} с | {c['reason']} | {text} | {flag} |")
    (d / "cuts.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    by_kind = {}
    for c in cuts:
        by_kind[c["kind"]] = by_kind.get(c["kind"], 0) + 1
    print(f"Склеек: {len(cuts)} {by_kind}. Вырезается ~{removed:.1f} с из {dur:.1f} с.")
    print(f"Таблица: {d / 'cuts.md'}")
    print(f"После «да»: python tools/apply_cuts.py {d.name}")


if __name__ == "__main__":
    main()
