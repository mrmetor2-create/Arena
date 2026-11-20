import React, { useMemo } from "react";
import { AbsoluteFill, Audio, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Captions } from "./Captions";
import { Overlays } from "./Overlays";
import type { MainProps, Project, Zoom } from "./types";

const zoomAt = (t: number, zooms: Zoom[], p: Project) => {
  const z = p.style.zoom;
  for (const zm of zooms) {
    if (t < zm.start || t >= zm.end) continue;
    const scale = zm.scale ?? z.defaultScale;
    const mode = zm.mode ?? z.mode;
    const ramp = mode === "cut" ? 0.001 : Math.min(0.25, (zm.end - zm.start) / 3);
    const k = interpolate(t, [zm.start, zm.start + ramp, zm.end - ramp, zm.end], [0, 1, 1, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    const eased = mode === "cut" ? (k > 0 ? 1 : 0) : k * k * (3 - 2 * k);
    return { scale: 1 + (scale - 1) * eased, x: zm.x ?? z.originX, y: zm.y ?? z.originY };
  }
  return { scale: 1, x: z.originX, y: z.originY };
};

const Guides: React.FC<{ p: Project }> = ({ p }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const s = p.style.safeZone;
  const band = "repeating-linear-gradient(45deg, rgba(255,0,60,0.55) 0 18px, rgba(0,0,0,0.35) 18px 36px)";
  const edge = "4px dashed #ff003c";
  const t = frame / fps;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ position: "absolute", left: 0, top: 0, width, height: s.top, background: band, borderBottom: edge }} />
      <div style={{ position: "absolute", left: 0, bottom: 0, width, height: s.bottom, background: band, borderTop: edge }} />
      <div style={{ position: "absolute", right: 0, top: s.top, width: s.right, height: height - s.top - s.bottom, background: band, borderLeft: edge }} />
      <div
        style={{
          position: "absolute", left: 24, top: 24, padding: "8px 18px", background: "rgba(0,0,0,0.75)",
          color: "#fff", fontFamily: "monospace", fontSize: 54, borderRadius: 12,
        }}
      >
        {`${Math.floor(t / 60)}:${(t % 60).toFixed(1).padStart(4, "0")}`}
      </div>
    </AbsoluteFill>
  );
};

const Music: React.FC<{ p: Project }> = ({ p }) => {
  const { fps, durationInFrames } = useVideoConfig();
  const m = p.edit.music;
  const base = m.volume ?? p.style.music.volume;
  const duck = p.style.music.duckVolume;
  // где идет речь (с запасом) — там музыку приглушаем
  const speech = useMemo(() => {
    const arr = new Float32Array(durationInFrames);
    for (const w of p.words) {
      const a = Math.max(0, Math.floor((w.start - 0.2) * fps));
      const b = Math.min(durationInFrames - 1, Math.ceil((w.end + 0.3) * fps));
      for (let f = a; f <= b; f++) arr[f] = 1;
    }
    // сглаживание ~0.25 с
    const win = Math.round(fps * 0.25);
    const out = new Float32Array(durationInFrames);
    for (let f = 0; f < durationInFrames; f++) {
      let sum = 0, n = 0;
      for (let k = -win; k <= win; k++) {
        const i = f + k;
        if (i >= 0 && i < durationInFrames) { sum += arr[i]; n++; }
      }
      out[f] = sum / n;
    }
    return out;
  }, [p.words, durationInFrames, fps]);

  if (!m.file) return null;
  const fadeOutFrames = Math.round(p.style.music.fadeOut * fps);
  return (
    <Audio
      src={staticFile(`current/music/${m.file}`)}
      loop
      trimBefore={Math.round((m.start_at ?? 0) * fps)}
      volume={(f) => {
        const v = base + (duck - base) * (speech[f] ?? 0);
        const fade = interpolate(f, [0, 8, durationInFrames - fadeOutFrames, durationInFrames], [0, 1, 1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        return v * fade;
      }}
    />
  );
};

export const Main: React.FC<MainProps> = ({ project, showGuides }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (!project) {
    return (
      <AbsoluteFill style={{ background: "#111", color: "#fff", justifyContent: "center", alignItems: "center", fontSize: 54, padding: 80, textAlign: "center", fontFamily: "Arial" }}>
        Нет проекта. Запусти: python tools/build_project.py &lt;ролик&gt;
      </AbsoluteFill>
    );
  }
  const p = project;
  const z = zoomAt(frame / fps, p.edit.zooms, p);
  const sfxVol = p.style.sfx.volume;

  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <AbsoluteFill style={{ transform: `scale(${z.scale})`, transformOrigin: `${z.x * 100}% ${z.y * 100}%` }}>
        <OffthreadVideo src={staticFile(p.video)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </AbsoluteFill>
      <Overlays overlays={p.edit.overlays} style={p.style} />
      <Captions words={p.words} style={p.style} overlays={p.edit.overlays} />
      <Music p={p} />
      {p.edit.sfx.map((s, i) => (
        <Sequence key={i} from={Math.max(0, Math.round(s.at * fps))} layout="none">
          <Audio src={staticFile(`current/sfx/${s.file}`)} volume={s.volume ?? sfxVol} />
        </Sequence>
      ))}
      {showGuides ? <Guides p={p} /> : null}
    </AbsoluteFill>
  );
};
