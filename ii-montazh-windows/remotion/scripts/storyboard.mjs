// Раскадровка без рендера: кадр каждые N секунд с субтитрами, графикой и разметкой сейф-зоны.
//   npm run storyboard            (кадр каждые 2.5 с)
//   npm run storyboard -- 2       (каждые 2 с)
import { renderStill } from "@remotion/renderer";
import fs from "node:fs";
import path from "node:path";
import { ROOT, browserExecutable, ffmpeg, prepare, readProject } from "./_common.mjs";

const every = Number(process.argv[2] || 2.5);
const project = readProject();
const outDir = path.join(ROOT, "work", project.name, "storyboard");
fs.rmSync(outDir, { recursive: true, force: true });
fs.mkdirSync(outDir, { recursive: true });

const inputProps = { showGuides: true };
const { serveUrl, composition } = await prepare(inputProps);
const fps = composition.fps;
const frames = [];
for (let t = 0.5; t * fps < composition.durationInFrames - 1; t += every) frames.push(Math.round(t * fps));

console.log(`Кадров в раскадровке: ${frames.length}`);
for (const [i, frame] of frames.entries()) {
  const output = path.join(outDir, `frame_${String(i + 1).padStart(3, "0")}.jpg`);
  await renderStill({ serveUrl, composition, frame, output, inputProps, scale: 0.4, imageFormat: "jpeg", jpegQuality: 85, browserExecutable });
  process.stdout.write(`\r  ${i + 1}/${frames.length}`);
}
console.log("");

// листы по 8 кадров (4x2) — их удобно смотреть целиком
const perSheet = 8;
const sheets = Math.ceil(frames.length / perSheet);
for (let s = 0; s < sheets; s++) {
  ffmpeg([
    "-start_number", String(s * perSheet + 1),
    "-i", path.join(outDir, "frame_%03d.jpg"),
    "-frames:v", "1",
    "-vf", "tile=4x2:padding=10:color=white",
    "-q:v", "3",
    path.join(outDir, `sheet_${String(s + 1).padStart(2, "0")}.jpg`),
  ]);
}
console.log(`Готово: ${outDir} (листы sheet_*.jpg, отдельные кадры frame_*.jpg; красное — зоны под кнопками Reels)`);
