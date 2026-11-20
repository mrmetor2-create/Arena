"""Шаг 4. Собирает проект для Remotion: видео, субтитры, стиль, правки, музыка, звуки.

    python tools/build_project.py ролик

Берет:
    work/<ролик>/cut.mp4, words.json
    style.json              — твой постоянный стиль (шрифт, цвета, сейф-зона, громкость музыки)
    work/<ролик>/edit.json  — правки этого ролика (зумы, плашки, звуки, музыка); создается, если нет
Кладет все в remotion/public/current/ — дальше превью (npm run studio), раскадровка и рендер.
Запускай заново после каждой правки edit.json / style.json / words.json.
"""
from __future__ import annotations

import argparse
import shutil

from common import FPS, HEIGHT, PUBLIC_CURRENT, ROOT, WIDTH, die, ffprobe, duration_of, load_json, resolve_work, save_json

DEFAULT_EDIT = {
    "_help": "Время — в секундах готового (смонтированного) ролика. После правки: python tools/build_project.py <ролик>",
    "music": {"file": "", "volume": None, "start_at": 0},
    "zooms": [],
    "overlays": [],
    "sfx": [],
}


def copy_if_newer(src, dst) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime or src.stat().st_size != dst.stat().st_size:
        shutil.copy2(src, dst)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    args = ap.parse_args()

    d = resolve_work(args.video)
    cut = d / "cut.mp4"
    if not cut.is_file():
        die("нет cut.mp4 — сначала apply_cuts.py")
    words = load_json(d / "words.json")["words"]
    style = load_json(ROOT / "style.json")

    edit_path = d / "edit.json"
    if not edit_path.exists():
        save_json(edit_path, DEFAULT_EDIT)
        print(f"Создан пустой {edit_path} — в него пишутся зумы, плашки, звуки и музыка.")
    edit = load_json(edit_path)

    # очистка прошлого ролика в public/current
    if PUBLIC_CURRENT.exists():
        shutil.rmtree(PUBLIC_CURRENT)
    PUBLIC_CURRENT.mkdir(parents=True)
    copy_if_newer(cut, PUBLIC_CURRENT / "cut.mp4")

    problems = []
    music = edit.get("music") or {}
    if music.get("file"):
        src = ROOT / "music" / music["file"]
        if src.is_file():
            copy_if_newer(src, PUBLIC_CURRENT / "music" / src.name)
        else:
            problems.append(f"нет музыки music/{music['file']}")
            music["file"] = ""
    for s in edit.get("sfx", []):
        src = ROOT / "sfx" / s.get("file", "")
        if src.is_file():
            copy_if_newer(src, PUBLIC_CURRENT / "sfx" / src.name)
        else:
            problems.append(f"нет звука sfx/{s.get('file')}")
            s["missing"] = True
    for o in edit.get("overlays", []):
        if o.get("image"):
            src = ROOT / "work" / d.name / o["image"]
            if not src.is_file():
                src = ROOT / o["image"]
            if src.is_file():
                copy_if_newer(src, PUBLIC_CURRENT / "img" / src.name)
                o["image"] = f"current/img/{src.name}"
            else:
                problems.append(f"нет картинки {o['image']}")
                o["image"] = ""

    duration = duration_of(ffprobe(cut))
    project = {
        "name": d.name,
        "fps": FPS,
        "width": WIDTH,
        "height": HEIGHT,
        "durationInFrames": max(1, int(round(duration * FPS))),
        "video": "current/cut.mp4",
        "words": words,
        "style": style,
        "edit": {
            "music": music,
            "zooms": edit.get("zooms", []),
            "overlays": edit.get("overlays", []),
            "sfx": [s for s in edit.get("sfx", []) if not s.get("missing")],
        },
    }
    save_json(PUBLIC_CURRENT / "project.json", project)
    print(f"Проект собран: {d.name}, {duration:.1f} с, слов {len(words)}, зумов {len(project['edit']['zooms'])}, "
          f"плашек {len(project['edit']['overlays'])}, звуков {len(project['edit']['sfx'])}, музыка: {music.get('file') or 'нет'}")
    for p in problems:
        print("ВНИМАНИЕ:", p)
    print("Превью: cd remotion && npm run studio   |   Раскадровка: cd remotion && npm run storyboard")


if __name__ == "__main__":
    main()
