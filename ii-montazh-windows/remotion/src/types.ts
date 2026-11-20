export type Word = { text: string; start: number; end: number };

export type Zoom = {
  start: number;
  end: number;
  scale?: number;
  /** 0..1 — точка, к которой приближаем (0.5/0.38 — примерно лицо) */
  x?: number;
  y?: number;
  mode?: "smooth" | "cut";
};

export type Overlay = {
  start: number;
  end: number;
  /** title — крупная плашка (хук), label — подпись, emoji — большой эмодзи, image — картинка */
  kind?: "title" | "label" | "emoji" | "image";
  text?: string;
  image?: string;
  /** центр по вертикали, px; по умолчанию — над субтитрами */
  y?: number;
  size?: number;
  /** прятать субтитры, пока висит плашка */
  hideCaptions?: boolean;
};

export type Sfx = { at: number; file: string; volume?: number };

export type Style = {
  safeZone: { top: number; bottom: number; left: number; right: number };
  captions: {
    enabled: boolean;
    font: string;
    weight: number;
    size: number;
    uppercase: boolean;
    color: string;
    highlight: string;
    stroke: string;
    strokeWidth: number;
    shadow: boolean;
    centerY: number;
    maxWords: number;
    maxChars: number;
    pop: boolean;
  };
  overlays: {
    font: string;
    weight: number;
    titleBg: string;
    titleColor: string;
    labelBg: string;
    labelColor: string;
    radius: number;
  };
  zoom: { defaultScale: number; mode: "smooth" | "cut"; originX: number; originY: number };
  music: { volume: number; duckVolume: number; fadeOut: number };
  sfx: { volume: number };
};

export type Project = {
  name: string;
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  video: string;
  words: Word[];
  style: Style;
  edit: {
    music: { file?: string; volume?: number | null; start_at?: number };
    zooms: Zoom[];
    overlays: Overlay[];
    sfx: Sfx[];
  };
};

export type MainProps = {
  project: Project | null;
  showGuides: boolean;
};
