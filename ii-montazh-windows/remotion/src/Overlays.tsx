import React from "react";
import { AbsoluteFill, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { useFont } from "./fonts";
import type { Overlay, Style } from "./types";

const OverlayItem: React.FC<{ o: Overlay; style: Style; durationFrames: number }> = ({ o, style, durationFrames }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const st = style.overlays;
  const s = style.safeZone;
  const family = useFont(st.font, st.weight);
  const kind = o.kind ?? "title";

  const inn = spring({ frame, fps, config: { damping: 13, stiffness: 200 }, durationInFrames: 10 });
  const out = interpolate(frame, [durationFrames - 6, durationFrames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const k = Math.min(inn, out);

  const defaultY = kind === "label" ? style.captions.centerY - 260 : s.top + 220;
  const y = Math.min(Math.max(o.y ?? defaultY, s.top + 60), height - s.bottom - 60);
  const maxW = width - s.left - s.right;

  let body: React.ReactNode = null;
  if (kind === "emoji") {
    body = <div style={{ fontSize: o.size ?? 220, lineHeight: 1 }}>{o.text}</div>;
  } else if (kind === "image" && o.image) {
    body = (
      <Img
        src={staticFile(o.image)}
        style={{ maxWidth: maxW, maxHeight: o.size ?? 620, borderRadius: st.radius, boxShadow: "0 18px 50px rgba(0,0,0,0.45)" }}
      />
    );
  } else {
    const title = kind === "title";
    body = (
      <div
        style={{
          maxWidth: maxW,
          padding: title ? "26px 40px" : "16px 30px",
          background: title ? st.titleBg : st.labelBg,
          color: title ? st.titleColor : st.labelColor,
          borderRadius: st.radius,
          fontFamily: `${family}, Arial, sans-serif`,
          fontWeight: st.weight,
          fontSize: o.size ?? (title ? 76 : 56),
          lineHeight: 1.1,
          textAlign: "center",
          boxShadow: "0 14px 40px rgba(0,0,0,0.35)",
        }}
      >
        {o.text}
      </div>
    );
  }

  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: s.left,
          width: maxW,
          top: y,
          display: "flex",
          justifyContent: "center",
          transform: `translateY(-50%) scale(${interpolate(k, [0, 1], [0.6, 1])})`,
          opacity: k,
        }}
      >
        {body}
      </div>
    </AbsoluteFill>
  );
};

export const Overlays: React.FC<{ overlays: Overlay[]; style: Style }> = ({ overlays, style }) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {overlays.map((o, i) => {
        const from = Math.round(o.start * fps);
        const dur = Math.max(1, Math.round((o.end - o.start) * fps));
        return (
          <Sequence key={i} from={from} durationInFrames={dur} layout="none">
            <OverlayItem o={o} style={style} durationFrames={dur} />
          </Sequence>
        );
      })}
    </>
  );
};
