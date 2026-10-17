// title3.mjs <icons.png> <title.png> "<line1 with [accent]>" "<line2>"
// icons: Claude + server rounded squares (reference style), title: Inter Tight 900, white + lime accent
import { chromium } from "playwright-core";
import { readFileSync } from "fs";
const [iconsOut, titleOut, l1, l2] = process.argv.slice(2);
const font = readFileSync(new URL("../edit/fonts/ReelSub.ttf", import.meta.url)).toString("base64");
const esc = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;");
const acc = (t) => esc(t).replace(/\[(.+?)\]/g, '<span style="color:#c8f04c">$1</span>');
const tile = (inner) => `<div class="tile">${inner}</div>`;
const claude = tile(`<svg width="128" height="128" viewBox="0 0 24 24"><path d="m4.7144 15.9555 4.7174-2.6471.079-.2307-.079-.1275h-.2307l-.7893-.0486-2.6956-.0729-2.3375-.0971-2.2646-.1214-.5707-.1215-.5343-.7042.0546-.3522.4797-.3218.686.0608 1.5179.1032 2.2767.1578 1.6514.0972 2.4468.255h.3886l.0546-.1579-.1336-.0971-.1032-.0972L6.973 9.8356l-2.55-1.6879-1.3356-.9714-.7225-.4918-.3643-.4614-.1578-1.0078.6557-.7225.8803.0607.2246.0607.8925.686 1.9064 1.4754 2.4893 1.8336.3643.3035.1457-.1032.0182-.0728-.164-.2733-1.3539-2.4467-1.445-2.4893-.6435-1.032-.17-.6194c-.0607-.255-.1032-.4674-.1032-.7285L6.287.1335 6.6997 0l.9957.1336.419.3642.6192 1.4147 1.0018 2.2282 1.5543 3.0296.4553.8985.2429.8318.091.255h.1579v-.1457l.1275-1.706.2368-2.0947.2307-2.6957.0789-.7589.3764-.9107.7468-.4918.5828.2793.4797.686-.0668.4433-.2853 1.8517-.5586 2.9021-.3643 1.9429h.2125l.2429-.2429.9835-1.3053 1.6514-2.0643.7286-.8196.85-.9046.5464-.4311h1.0321l.759 1.1293-.34 1.1657-1.0625 1.3478-.8804 1.1414-1.2628 1.7-.7893 1.36.0729.1093.1882-.0183 2.8535-.607 1.5421-.2794 1.8396-.3157.8318.3886.091.3946-.3278.8075-1.967.4857-2.3072.4614-3.4364.8136-.0425.0304.0486.0607 1.5482.1457.6618.0364h1.621l3.0175.2247.7892.522.4736.6376-.079.4857-1.2142.6193-1.6393-.3886-3.825-.9107-1.3113-.3279h-.1822v.1093l1.0929 1.0686 2.0035 1.8092 2.5075 2.3314.1275.5768-.3218.4554-.34-.0486-2.2039-1.6575-.85-.7468-1.9246-1.621h-.1275v.17l.4432.6496 2.3436 3.5214.1214 1.0807-.17.3521-.6071.2125-.6679-.1214-1.3721-1.9246L14.38 17.959l-1.1414-1.9428-.1397.079-.674 7.2552-.3156.3703-.7286.2793-.6071-.4614-.3218-.7468.3218-1.4753.3886-1.9246.3157-1.53.2853-1.9004.17-.6314-.0121-.0425-.1397.0182-1.4328 1.9672-2.1796 2.9446-1.7243 1.8456-.4128.164-.7164-.3704.0667-.6618.4008-.5889 2.386-3.0357 1.4389-1.882.929-1.0868-.0062-.1579h-.0546l-6.3385 4.1164-1.1293.1457-.4857-.4554.0608-.7467.2307-.2429 1.9064-1.3114Z" fill="#D97757"/></svg>`);
const server = tile(`<svg width="120" height="120" viewBox="0 0 24 24" fill="none">
 <rect x="3" y="3.5" width="18" height="7" rx="2" fill="#2a2a2a"/><rect x="3" y="13.5" width="18" height="7" rx="2" fill="#2a2a2a"/>
 <circle cx="7" cy="7" r="1.2" fill="#c8f04c"/><circle cx="7" cy="17" r="1.2" fill="#c8f04c"/>
 <rect x="11" y="6.3" width="7" height="1.4" rx=".7" fill="#777"/><rect x="11" y="16.3" width="7" height="1.4" rx=".7" fill="#777"/></svg>`);
const css = `@font-face{font-family:RS;src:url(data:font/ttf;base64,${font})}
html,body{margin:0;background:transparent}
.tile{width:190px;height:190px;border-radius:44px;background:#fff;display:flex;align-items:center;justify-content:center;box-shadow:0 10px 34px rgba(0,0,0,.28)}
.icons{display:flex;align-items:center;gap:34px;padding:40px}
.plus{font-family:RS;font-size:76px;color:#fff;text-shadow:0 2px 12px rgba(0,0,0,.35);line-height:1;margin-top:-6px}
.wrap{position:absolute;left:40px;width:1000px;top:${360}px;text-align:center;font-family:RS;color:#fff;letter-spacing:-0.035em;line-height:1.02}
.l{white-space:nowrap;display:inline-block;font-size:112px;text-shadow:0 3px 6px rgba(0,0,0,.3),0 6px 30px rgba(0,0,0,.35)}`;
const b = await chromium.launch({ channel: "chrome", headless: true });
let p = await b.newPage({ viewport: { width: 600, height: 300 } });
await p.setContent(`<html><head><style>${css}</style></head><body><div class="icons" id="i">${claude}<div class="plus">+</div>${server}</div></body></html>`);
await p.evaluate(() => document.fonts.ready);
const box = await (await p.$("#i")).boundingBox();
await p.screenshot({ path: iconsOut, omitBackground: true, clip: box });
p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
await p.setContent(`<html><head><style>${css}</style></head><body><div class="wrap"><div class="l">${acc(l1)}</div><br><div class="l">${acc(l2)}</div></div></body></html>`);
await p.evaluate(() => document.fonts.ready);
const px = await p.evaluate(() => { const ls = [...document.querySelectorAll(".l")]; let s = 112;
  while (ls.some((l) => l.getBoundingClientRect().width > 980) && s > 60) { s -= 2; ls.forEach((l) => (l.style.fontSize = s + "px")); } return s; });
await p.screenshot({ path: titleOut, omitBackground: true }); await b.close();
console.log(titleOut.split("/").pop(), px + "px", Math.round(box.width) + "x" + Math.round(box.height));
