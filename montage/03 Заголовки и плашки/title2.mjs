// title2.mjs <out.png> "<label>" "<title>"  — label small above, bold white title one line, soft shadow
import { chromium } from "playwright-core";
const [out, label, title] = process.argv.slice(2);
const esc = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;");
const html = `<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;width:1080px;height:1920px;background:transparent}
.wrap{position:absolute;left:50px;width:980px;top:340px;text-align:center;font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;color:#fff}
.label{font-weight:500;font-size:34px;line-height:1;margin-bottom:26px;text-shadow:0 1px 3px rgba(0,0,0,.45),0 2px 14px rgba(0,0,0,.35)}
.title{font-weight:700;font-size:88px;line-height:1.05;letter-spacing:-0.02em;white-space:nowrap;display:inline-block;
  text-shadow:0 2px 4px rgba(0,0,0,.35),0 4px 24px rgba(0,0,0,.4)}
</style></head><body><div class="wrap"><div class="label">${esc(label)}</div><div class="title">${esc(title)}</div></div></body></html>`;
const b = await chromium.launch({ channel: "chrome", headless: true });
const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
await p.setContent(html); await p.evaluate(() => document.fonts.ready);
const px = await p.evaluate(() => { const t = document.querySelector(".title"); let s = 88;
  while (t.getBoundingClientRect().width > 980 && s > 56) { s -= 2; t.style.fontSize = s + "px"; } return s; });
await p.screenshot({ path: out, omitBackground: true }); await b.close();
console.log(out.split("/").pop(), px + "px");
