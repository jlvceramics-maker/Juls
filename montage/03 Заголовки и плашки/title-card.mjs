#!/usr/bin/env node
// Триггерный заголовок поверх готового рилса.
//
//   node title-card.mjs <in.mp4> <out.mp4> --title "Скиллы в Claude [больше не нужны]?"
//        [--label "..."] [--font fonts/Unbounded.ttf] [--hand fonts/MartinaScriptC.ttf] [--size 64] [--png-only 1]
//
// Слова в квадратных скобках пишутся рукописным шрифтом лаймом.
// Плашек нет: сверху кадра мягкое затемнение, на нём белый заголовок читается и на светлой стене.
// Геометрия: текст начинается на y=250 (выше перекрывает интерфейс Instagram)
// и не должен уходить ниже y=500 (у спикера глаза начинаются около y=480-600).
//
// Radius с dafont (fonts/radius-latin-only.ttf) без кириллицы: русские буквы в нём не набираются.
import { chromium } from "playwright-core";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const flags = {};
const pos = [];
for (let i = 0; i < args.length; i++) {
  if (args[i].startsWith("--")) { flags[args[i].slice(2)] = args[i + 1]; i++; } else pos.push(args[i]);
}
const [input, output] = pos;
if (!input || !output || !flags.title) {
  console.error('usage: title-card.mjs <in.mp4> <out.mp4> --title "..." [--label "..."] [--font f.ttf] [--hand f.ttf]');
  process.exit(1);
}

const fontPath = path.resolve(HERE, flags.font ?? "../04 Шрифты/Unbounded.ttf");
const handPath = path.resolve(HERE, flags.hand ?? "../04 Шрифты/Caveat.ttf");
const dataUrl = (p) => `data:font/ttf;base64,${readFileSync(p).toString("base64")}`;

// Лайм #C8F04C. На затемнённом видео он читается и как цвет текста.
const C = { white: "#FFFFFF", lime: "#C8F04C" };
const TOP = 250, MAX_BOTTOM = 500;
const size = Number(flags.size ?? 86);
const weight = flags.weight ?? "400";
// Размер рукописного слова относительно заголовка. У узкого Radius хватает 1.0, у широкого Unbounded 1.55.
const handScale = Number(flags["hand-scale"] ?? 1.25);

const esc = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const titleHtml = esc(flags.title).replace(/\[([^\]]+)\]/g, `<span class="hand">$1<svg viewBox="0 0 300 24" preserveAspectRatio="none"><path d="M4 16 C80 6, 200 22, 296 8" stroke="${C.lime}" stroke-width="6" fill="none" stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg></span>`);
const labelHtml = flags.label ? `<div class="label">${esc(flags.label)}</div>` : "";

const html = `<!doctype html><html><head><meta charset="utf-8"><style>
  @font-face { font-family: Head; src: url(${dataUrl(fontPath)}); font-weight: 100 900; }
  @font-face { font-family: Hand; src: url(${dataUrl(handPath)}); font-weight: 100 900; }
  html, body { margin: 0; width: 1080px; height: 1920px; background: transparent; }
  .shade { position: absolute; left: 0; top: 0; width: 1080px; height: 820px;
    background: linear-gradient(to bottom, rgba(17,17,17,0.62) 0%, rgba(17,17,17,0.42) 45%, rgba(17,17,17,0) 100%); }
  .wrap { position: absolute; left: 60px; top: ${TOP}px; width: 960px; text-align: center; }
  .label { font: 500 24px/1 Head, sans-serif; letter-spacing: 0.14em; text-transform: uppercase;
    color: rgba(255,255,255,0.78); margin-bottom: 22px; }
  .title { font: ${weight} ${size}px/1.14 Head, sans-serif; letter-spacing: -0.01em; color: ${C.white};
    text-wrap: balance; text-shadow: 0 2px 18px rgba(0,0,0,0.35); }
  /* Рукописный кусок держится одним блоком: не переносится, подчёркивание всегда ровно по его ширине. */
  .hand { font-family: Hand, cursive; font-weight: 700; font-size: ${handScale}em; line-height: 0.9; letter-spacing: 0;
    color: ${C.lime}; display: inline-block; white-space: nowrap; position: relative; vertical-align: baseline;
    padding: 0 0.06em 0.12em; text-shadow: 0 3px 14px rgba(0,0,0,0.5); }
  .hand svg { position: absolute; left: 2%; bottom: -0.02em; width: 96%; height: 0.28em; overflow: visible; }
</style></head><body><div class="shade"></div><div class="wrap">${labelHtml}<div class="title">${titleHtml}</div></div></body></html>`;

const tmp = mkdtempSync(path.join(tmpdir(), "title-"));
const png = path.join(tmp, "title.png");
try {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.setContent(html);
  await page.evaluate(() => document.fonts.ready);
  const fit = await page.evaluate(({ max, min }) => {
    const wrap = document.querySelector(".wrap"), title = document.querySelector(".title");
    let px = parseFloat(getComputedStyle(title).fontSize);
    const ok = () => {
      const w = wrap.getBoundingClientRect();
      const tooWide = [...document.querySelectorAll(".hand")].some((h) => { const r = h.getBoundingClientRect(); return r.left < w.left - 1 || r.right > w.right + 1; });
      return w.bottom <= max && !tooWide && title.scrollWidth <= wrap.clientWidth + 1;
    };
    while (!ok() && px > min) { px -= 2; title.style.fontSize = px + "px"; }
    return { px, bottom: wrap.getBoundingClientRect().bottom, fits: ok() };
  }, { max: MAX_BOTTOM, min: 54 });
  const bottom = fit.bottom;
  console.log(`размер ${fit.px}px${fit.px < size ? ` (уменьшен с ${size})` : ""}`);
  if (!fit.fits) console.error("внимание: даже на минимальном размере заголовок не влезает, сократи текст");
  await page.screenshot({ path: png, omitBackground: true });
  await browser.close();
  if (bottom > MAX_BOTTOM) console.error(`внимание: текст доходит до y=${Math.round(bottom)}, ниже ${MAX_BOTTOM} он заденет лицо. Сократи заголовок или уменьши --size.`);
  else console.log(`заголовок y=${TOP}..${Math.round(bottom)}`);

  if (flags["png-only"]) { spawnSync("cp", [png, output]); process.exit(0); }

  const res = spawnSync("ffmpeg", ["-v", "error", "-y", "-i", input, "-loop", "1", "-i", png,
    "-filter_complex", "[1:v]format=rgba,fade=in:st=0.1:d=0.35:alpha=1[t];[0:v][t]overlay=0:0:shortest=1,format=yuv420p[v]",
    "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-maxrate", "2400k", "-bufsize", "4800k",
    "-c:a", "copy", "-movflags", "+faststart", output], { encoding: "utf8" });
  if (res.status !== 0) { console.error(res.stderr); process.exit(1); }
  console.log(output);
} finally {
  rmSync(tmp, { recursive: true, force: true });
}
