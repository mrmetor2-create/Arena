import { bundle } from "@remotion/bundler";
import { selectComposition } from "@remotion/renderer";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const REMOTION_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const ROOT = path.resolve(REMOTION_DIR, "..");

export const readProject = () => {
  const p = path.join(REMOTION_DIR, "public", "current", "project.json");
  if (!fs.existsSync(p)) {
    console.error("Нет проекта. Сначала: python tools/build_project.py <ролик>");
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(p, "utf-8"));
};

// Для отладки на Linux/CI можно указать свой Chrome; на Windows Remotion скачает его сам.
export const browserExecutable = process.env.REMOTION_BROWSER || null;

export const prepare = async (inputProps) => {
  console.log("Собираю проект Remotion...");
  const serveUrl = await bundle({
    entryPoint: path.join(REMOTION_DIR, "src", "index.ts"),
    publicDir: path.join(REMOTION_DIR, "public"),
  });
  const composition = await selectComposition({ serveUrl, id: "Main", inputProps, browserExecutable });
  return { serveUrl, composition };
};

export const ffmpeg = (args) => {
  const r = spawnSync("ffmpeg", ["-y", "-hide_banner", "-loglevel", "error", ...args], { stdio: "inherit" });
  if (r.status !== 0) {
    console.error("ffmpeg завершился с ошибкой");
    process.exit(1);
  }
};
