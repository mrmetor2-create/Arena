// Финальный рендер + выравнивание громкости под Reels (-14 LUFS).
//   npm run render
//   npm run render -- draft      (быстрый черновик в половинном размере)
import { renderMedia } from "@remotion/renderer";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { ROOT, browserExecutable, ffmpeg, prepare, readProject } from "./_common.mjs";

const draft = process.argv[2] === "draft";
const project = readProject();
const workDir = path.join(ROOT, "work", project.name);
const raw = path.join(workDir, draft ? "render_draft_raw.mp4" : "render_raw.mp4");
const outDir = path.join(ROOT, "output");
fs.mkdirSync(outDir, { recursive: true });
const final = path.join(outDir, `${project.name}${draft ? "_draft" : ""}.mp4`);

const inputProps = { showGuides: false };
const { serveUrl, composition } = await prepare(inputProps);
const started = Date.now();
let lastPct = -1;
await renderMedia({
  serveUrl,
  composition,
  codec: "h264",
  crf: draft ? 26 : 18,
  scale: draft ? 0.5 : 1,
  outputLocation: raw,
  inputProps,
  browserExecutable,
  concurrency: Math.max(1, Math.floor(os.cpus().length / 2)),
  onProgress: ({ progress }) => {
    const pct = Math.floor(progress * 10) * 10;
    if (pct !== lastPct) {
      lastPct = pct;
      console.log(`  рендер ${pct}%`);
    }
  },
});
console.log(`\nРендер за ${((Date.now() - started) / 1000).toFixed(0)} с. Выравниваю громкость...`);
ffmpeg(["-i", raw, "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", final]);
console.log(`Готово: ${final}`);
