// Железная проверка бесшовности: кадр при фазе 0 и при фазе 2PI обязаны совпасть
// попиксельно. Зерно выключено, кодек не участвует — сравниваются сырые кадры.
import { chromium } from 'playwright-core';
import { execFileSync } from 'node:child_process';
import { writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const STYLES = process.argv.slice(2);
if (!STYLES.length) { console.error('usage: node checkloop.mjs <style:mode> ...'); process.exit(1); }

const browser = await chromium.launch({
  executablePath: CHROME,
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files']
});
const dir = mkdtempSync(join(tmpdir(), 'loopcheck-'));
let bad = 0;

for (const job of STYLES) {
  const [style, mode = 'dark'] = job.split(':');
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto(`file://${import.meta.dirname}/frame.html?style=${style}&mode=${mode}&grain=0`);
  await page.waitForFunction('window.__ready === true');
  const shot = async phase => {
    await page.evaluate(p => window.__draw(p), phase);
    return page.locator('#c').screenshot({ type: 'png', animations: 'disabled' });
  };
  const a = join(dir, `${style}-${mode}-a.png`);
  const b = join(dir, `${style}-${mode}-b.png`);
  writeFileSync(a, await shot(0));
  writeFileSync(b, await shot(2 * Math.PI));
  await page.close();

  // сравнение через ffmpeg: PSNR бесконечен, когда кадры идентичны
  const out = execFileSync('ffmpeg', ['-v', 'error', '-i', a, '-i', b,
    '-lavfi', 'psnr', '-f', 'null', '-'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
  const raw = execFileSync('bash', ['-c',
    `ffmpeg -v info -i "${a}" -i "${b}" -lavfi psnr -f null - 2>&1 | grep -o 'average:[^ ]*'`],
    { encoding: 'utf8' }).trim();
  // 60 дБ и выше — кадры визуально идентичны; ниже означает непериодичное движение
  const db = /inf/i.test(raw) ? Infinity : Number((raw.match(/average:([\d.]+)/) || [])[1] || 0);
  const ok = db >= 60;
  if (!ok) bad++;
  console.log(`${ok ? 'OK  ' : 'РВЁТ'} ${style}/${mode}  psnr ${db === Infinity ? 'inf' : db.toFixed(1)} дБ`);
}

await browser.close();
process.exit(bad ? 1 : 0);
