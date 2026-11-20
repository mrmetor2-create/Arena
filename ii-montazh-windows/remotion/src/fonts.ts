import { loadFont as inter } from "@remotion/google-fonts/Inter";
import { loadFont as manrope } from "@remotion/google-fonts/Manrope";
import { loadFont as montserrat } from "@remotion/google-fonts/Montserrat";
import { loadFont as oswald } from "@remotion/google-fonts/Oswald";
import { loadFont as rubik } from "@remotion/google-fonts/Rubik";
import { loadFont as unbounded } from "@remotion/google-fonts/Unbounded";

// Шрифты с кириллицей. Нужен другой — добавь импорт из @remotion/google-fonts.
const LOADERS: Record<string, (style?: any, options?: any) => { fontFamily: string }> = {
  Inter: inter,
  Manrope: manrope,
  Montserrat: montserrat,
  Oswald: oswald,
  Rubik: rubik,
  Unbounded: unbounded,
};

const cache = new Map<string, string>();

export const useFont = (name: string, weight: number): string => {
  const key = `${name}:${weight}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const loader = LOADERS[name];
  let family = `${name}, Arial, sans-serif`;
  if (loader) {
    try {
      family = loader("normal", { weights: [String(weight)], subsets: ["cyrillic", "latin"] }).fontFamily;
    } catch {
      // у шрифта нет такой жирности — грузим все начертания
      family = loader("normal", { subsets: ["cyrillic", "latin"], ignoreTooManyRequestsWarning: true }).fontFamily;
    }
  }
  cache.set(key, family);
  return family;
};
