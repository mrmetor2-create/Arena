import React, { useMemo } from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useFont } from "./fonts";
import type { Overlay, Style, Word } from "./types";

type Page = { start: number; end: number; words: Word[] };

const ENDS_PHRASE = /[.!?…:;]$/;

/** Делим слова на «страницы» по 1–3 слова: по паузам, знакам препинания и длине строки. */
export const toPages = (words: Word[], maxWords: number, maxChars: number): Page[] => {
  const pages: Page[] = [];
  let cur: Word[] = [];
  const flush = () => {
    if (cur.length) pages.push({ start: cur[0].start, end: cur[cur.length - 1].end, words: cur });
    cur = [];
  };
  words.forEach((w, i) => {
    const prev = words[i - 1];
    const chars = cur.reduce((n, x) => n + x.text.length + 1, 0) + w.text.length;
    if (cur.length && (cur.length >= maxWords || chars > maxChars || (prev && w.start - prev.end > 0.45))) flush();
    cur.push(w);
    if (ENDS_PHRASE.test(w.text)) flush();
  });
  flush();
  // страница держится до следующей (если пауза короткая), чтобы текст не мигал
  for (let i = 0; i < pages.length - 1; i++) {
    const gap = pages[i + 1].start - pages[i].end;
    pages[i].end += gap < 0.6 ? gap : 0.25;
  }
  if (pages.length) pages[pages.length - 1].end += 0.4;
  return pages;
};

export const Captions: React.FC<{ words: Word[]; style: Style; overlays: Overlay[] }> = ({ words, style, overlays }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const c = style.captions;
  const s = style.safeZone;
  const family = useFont(c.font, c.weight);
  const pages = useMemo(() => toPages(words, c.maxWords, c.maxChars), [words, c.maxWords, c.maxChars]);
  const t = frame / fps;

  if (!c.enabled) return null;
  if (overlays.some((o) => o.hideCaptions && t >= o.start && t < o.end)) return null;
  const page = pages.find((p) => t >= p.start && t < p.end);
  if (!page) return null;

  const pageFrame = frame - Math.round(page.start * fps);
  const appear = c.pop ? spring({ frame: pageFrame, fps, config: { damping: 14, stiffness: 220 }, durationInFrames: 8 }) : 1;
  const minY = s.top + c.size;
  const maxY = height - s.bottom - c.size;
  const centerY = Math.min(Math.max(c.centerY, minY), maxY);
  const shadow = c.shadow ? "0 6px 18px rgba(0,0,0,0.45)" : "none";

  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: s.left,
          width: width - s.left - s.right,
          top: centerY,
          transform: `translateY(-50%) scale(${interpolate(appear, [0, 1], [0.85, 1])})`,
          opacity: appear,
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          alignItems: "center",
          columnGap: c.size * 0.28,
          rowGap: c.size * 0.05,
          fontFamily: `${family}, Arial, sans-serif`,
          fontWeight: c.weight,
          fontSize: c.size,
          lineHeight: 1.12,
          textAlign: "center",
          textTransform: c.uppercase ? "uppercase" : "none",
        }}
      >
        {page.words.map((w, i) => {
          const active = t >= w.start && t < (page.words[i + 1]?.start ?? page.end);
          const wf = frame - Math.round(w.start * fps);
          const bump = c.pop && active ? interpolate(wf, [0, 3, 7], [1, 1.12, 1.06], { extrapolateRight: "clamp" }) : 1;
          return (
            <span
              key={i}
              style={{
                color: active ? c.highlight : c.color,
                WebkitTextStroke: `${c.strokeWidth}px ${c.stroke}`,
                paintOrder: "stroke fill",
                textShadow: shadow,
                display: "inline-block",
                transform: `scale(${bump})`,
              }}
            >
              {w.text}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
