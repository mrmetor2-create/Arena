"""Общие функции для скриптов монтажа (Windows/Mac/Linux)."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
REMOTION = ROOT / "remotion"
PUBLIC_CURRENT = REMOTION / "public" / "current"
FPS = 30
WIDTH = 1080
HEIGHT = 1920

# Консоль Windows и пайпы Claude Code: печатаем в UTF-8 без падений.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def die(msg: str) -> None:
    print(f"ОШИБКА: {msg}", file=sys.stderr)
    sys.exit(1)


def need(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        die(f"не найден {tool}. Запусти install.ps1 или поставь {tool} вручную.")
    return path


def run(cmd: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    res = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if res.returncode != 0:
        if capture:
            print(res.stderr[-3000:], file=sys.stderr)
        die(f"команда завершилась с кодом {res.returncode}: {' '.join(cmd[:3])} ...")
    return res


def ffprobe(path: Path) -> dict:
    need("ffprobe")
    res = run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        capture=True,
    )
    return json.loads(res.stdout)


def video_stream(info: dict) -> dict | None:
    return next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)


def audio_stream(info: dict) -> dict | None:
    return next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)


def duration_of(info: dict) -> float:
    return float(info.get("format", {}).get("duration") or 0)


def ffmpeg_filters() -> str:
    return run(["ffmpeg", "-hide_banner", "-filters"], capture=True).stdout


def ffmpeg_major() -> int:
    out = run(["ffmpeg", "-hide_banner", "-version"], capture=True).stdout
    m = re.search(r"ffmpeg version n?(\d+)", out)
    return int(m.group(1)) if m else 6


def stem_dir(name_or_path: str) -> Path:
    """work/<имя ролика>/ — по имени исходника или папки."""
    p = Path(name_or_path)
    stem = p.stem if p.suffix else p.name
    d = WORK / stem
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve_work(arg: str) -> Path:
    """Принимает имя ролика, путь к исходнику или к папке work/<имя>."""
    p = Path(arg)
    if p.is_dir():
        return p.resolve()
    d = WORK / (p.stem if p.suffix else p.name)
    if not d.is_dir():
        die(f"нет рабочей папки {d}. Сначала запусти prepare.py для этого ролика.")
    return d


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def ts(sec: float) -> str:
    """12.34 -> 00:12.3"""
    sec = max(0.0, sec)
    m = int(sec // 60)
    return f"{m:02d}:{sec - m * 60:04.1f}"


_PUNCT = re.compile(r"[^\w\-]+", re.UNICODE)


def norm(word: str) -> str:
    return _PUNCT.sub("", word.lower().replace("ё", "е")).strip("-")


def snap(t: float, fps: int = FPS) -> float:
    """Округление до кадра, чтобы звук и видео не разъезжались после склеек."""
    return round(t * fps) / fps
