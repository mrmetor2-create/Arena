"""Шаг 0. Рабочая копия исходника: 1080x1920, H.264, SDR, ровно 30 fps, звук 48 кГц.

Зачем: видео с iPhone обычно HEVC + HDR + плавающая частота кадров.
В Remotion это дает пересвет/блеклые цвета и рассинхрон звука.

    python tools/prepare.py input/ролик.mov
    python tools/prepare.py input/ролик.mov --fit blur      # горизонтальное видео: размытый фон вместо обрезки
    python tools/prepare.py input/ролик.mov --clean-audio   # срезать гул и легкий шум
"""
from __future__ import annotations

import argparse
from pathlib import Path

from common import FPS, HEIGHT, WIDTH, audio_stream, die, duration_of, ffmpeg_filters, ffprobe, need, run, save_json, stem_dir, video_stream

HDR_TRANSFERS = {"smpte2084", "arib-std-b67"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--fit", choices=["crop", "blur"], default="crop", help="как вписать не-вертикальное видео в 9:16")
    ap.add_argument("--clean-audio", action="store_true", help="highpass 80 Гц + мягкое шумоподавление")
    ap.add_argument("--crf", type=int, default=18)
    args = ap.parse_args()

    need("ffmpeg")
    src = Path(args.input)
    if not src.is_file():
        die(f"нет файла {src}")
    info = ffprobe(src)
    v = video_stream(info)
    a = audio_stream(info)
    if not v:
        die("в файле нет видео")

    out_dir = stem_dir(str(src))
    out = out_dir / "proxy.mp4"

    filters: list[str] = []
    transfer = (v.get("color_transfer") or "").lower()
    is_hdr = transfer in HDR_TRANSFERS
    if is_hdr:
        if "zscale" in ffmpeg_filters():
            filters.append(
                "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
                "tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv"
            )
        else:
            print("ВНИМАНИЕ: HDR-видео, но в ffmpeg нет zscale — цвета могут быть блеклыми. Поставь полную сборку Gyan.FFmpeg.")

    # ffmpeg сам поворачивает видео по метаданным телефона.
    if args.fit == "crop":
        filters.append(f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT}")
        vf = ",".join(filters + [f"fps={FPS}", "setsar=1", "format=yuv420p"])
        vargs = ["-vf", vf]
    else:
        pre = (",".join(filters) + ",") if filters else ""
        fc = (
            f"[0:v]{pre}split[a][b];"
            f"[a]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},boxblur=30:2[bg];"
            f"[b]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,fps={FPS},setsar=1,format=yuv420p[v]"
        )
        vargs = ["-filter_complex", fc, "-map", "[v]", "-map", "0:a?"]

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), *vargs]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-fps_mode", "cfr", "-movflags", "+faststart"]
    if a:
        af = ["aresample=48000"]
        if args.clean_audio:
            af = ["highpass=f=80", "afftdn=nf=-25"] + af
        cmd += ["-af", ",".join(af), "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-ar", "48000"]
    else:
        print("ВНИМАНИЕ: в исходнике нет звука — субтитры сделать не получится.")
    cmd.append(str(out))

    print(f"Готовлю рабочую копию: {src.name} -> {out}")
    print(f"  HDR: {'да, перевожу в SDR' if is_hdr else 'нет'}; вписывание: {args.fit}")
    run(cmd)

    pinfo = ffprobe(out)
    meta = {
        "source": str(src.resolve()),
        "proxy": str(out),
        "duration": duration_of(pinfo),
        "fps": FPS,
        "width": WIDTH,
        "height": HEIGHT,
        "source_codec": v.get("codec_name"),
        "source_hdr": is_hdr,
        "source_size": f"{v.get('width')}x{v.get('height')}",
    }
    save_json(out_dir / "meta.json", meta)
    print(f"Готово: {out} ({meta['duration']:.1f} с). Дальше: python tools/transcribe.py {out_dir.name}")


if __name__ == "__main__":
    main()
