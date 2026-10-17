// Покадровый рендер подложки в mp4. Кадры идут в ffmpeg через stdin, на диск не пишутся.
// Луп бесшовный: фаза пробегает ровно 0..2PI за LOOP секунд, последний кадр не дублирует первый.
import { chromium } from 'playwright-core';
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const W = 1080, H = 1920, FPS = 30, LOOP = 20;
const TOTAL = FPS * LOOP;

const [style, mode, outArg] = process.argv.slice(2);
if (!style || !mode || !outArg) {
  console.error('usage: node render.mjs <style> <dark|light> <out.mp4>');
  process.exit(1);
}
const out = resolve(outArg);
mkdirSync(dirname(out), { recursive: true });

const browser = await chromium.launch({
  executablePath: CHROME,
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files']
});
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
const url = `file://${import.meta.dirname}/frame.html?style=${style}&mode=${mode}`;
await page.goto(url);
await page.waitForFunction('window.__ready === true');
const canvas = page.locator('#c');

const ff = spawn('ffmpeg', [
  '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', 'pipe:0',
  '-an', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
  '-pix_fmt', 'yuv420p', '-g', String(FPS), '-movflags', '+faststart', out
], { stdio: ['pipe', 'ignore', 'inherit'] });

for (let i = 0; i < TOTAL; i++) {
  const phase = (i / TOTAL) * 2 * Math.PI;
  await page.evaluate(p => window.__draw(p), phase);
  const png = await canvas.screenshot({ type: 'png', animations: 'disabled' });
  if (!ff.stdin.write(png)) await new Promise(r => ff.stdin.once('drain', r));
  if (i % 60 === 0) process.stderr.write(`${style}/${mode}: ${i}/${TOTAL}\n`);
}
ff.stdin.end();
await new Promise((res, rej) => ff.on('close', c => (c === 0 ? res() : rej(new Error('ffmpeg ' + c)))));
await browser.close();
console.log(`done ${out}`);
