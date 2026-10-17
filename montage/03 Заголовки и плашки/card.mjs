// card.mjs <spec.json> : renders 1080x1920 transparent PNGs with a white card holding report crops + lime highlights
import { chromium } from "playwright-core";
import { readFileSync } from "fs";
const specs = JSON.parse(readFileSync(process.argv[2], "utf8"));
const font = readFileSync(new URL("../edit/fonts/ReelSub.ttf", import.meta.url)).toString("base64");
const W = 1012, BOTTOM = 1555;
const b = await chromium.launch({ channel: "chrome", headless: true });
const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
const imgs = {};
for (const s of specs) {
  const src = s.src;
  if (!imgs[src]) imgs[src] = "data:image/png;base64," + readFileSync(src).toString("base64");
  const s0 = W / Math.max(...s.parts.map((q) => q.crop[2]));
  let y = 0, html = "";
  const placed = s.parts.map((q) => {
    const sc = (q.scale || 1) * s0, [cx, cy, cw, ch] = q.crop;
    const w = cw * sc, h = ch * sc, x = (W - w) / 2;
    const r = { x, y, sc, cx, cy };
    html += `<div style="position:absolute;left:${x}px;top:${y}px;width:${w}px;height:${h}px;overflow:hidden">
      <img src="${imgs[src]}" style="position:absolute;left:${-cx * sc}px;top:${-cy * sc}px;width:${s.srcW * sc}px"></div>`;
    y += h + (q.gap ?? 14);
    return r;
  });
  for (const h of s.hl || []) {
    const r = placed[h.part || 0], [hx, hy, hw, hh] = h.box;
    const L = r.x + (hx - r.cx) * r.sc, T = r.y + (hy - r.cy) * r.sc;
    const rad = h.circle ? "50%" : "10px";
    html += `<div style="position:absolute;left:${L - 5}px;top:${T - 5}px;width:${hw * r.sc}px;height:${hh * r.sc}px;border:5px solid #c8f04c;border-radius:${rad};box-shadow:0 0 0 2px rgba(0,0,0,.55),inset 0 0 0 2px rgba(0,0,0,.35)"></div>`;
  }
  const innerH = y - 14;
  const cap = s.caption ? `<div class="cap">${s.caption.replace(/\[(.+?)\]/g, '<b>$1</b>')}</div>` : "";
  const src_l = `<div class="src">github.com/calesthio/OpenMontage</div>`;
  await p.setContent(`<html><head><style>@font-face{font-family:RS;src:url(data:font/ttf;base64,${font})}
  html,body{margin:0;background:transparent}
  .card{position:absolute;left:34px;width:${W}px;background:#fff;border-radius:30px;padding:22px 0 18px;box-shadow:0 14px 50px rgba(0,0,0,.38)}
  .cap{font-family:RS;font-size:44px;letter-spacing:-0.02em;color:#111;text-align:center;padding:0 24px 14px;line-height:1.05}
  .cap b{background:#c8f04c;padding:0 10px;border-radius:8px;font-weight:inherit}
  .src{font-family:-apple-system,Helvetica Neue,sans-serif;font-size:21px;color:#888;text-align:center;padding-top:12px}
  .in{position:relative;width:${W}px;height:${innerH}px}</style></head>
  <body><div class="card" id="c">${cap}<div class="in">${html}</div>${src_l}</div></body></html>`);
  await p.evaluate(() => Promise.all([document.fonts.ready, ...[...document.images].map((i) => i.decode())]));
  const ch = await p.evaluate(() => document.getElementById("c").offsetHeight);
  await p.evaluate((t) => (document.getElementById("c").style.top = t + "px"), BOTTOM - ch);
  await p.screenshot({ path: s.out, omitBackground: true });
  console.log(s.out.split("/").pop(), "card h", ch, "top", BOTTOM - ch);
}
await b.close();
