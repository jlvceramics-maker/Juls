// Батч-рендер всех подложек. Параллелит по числу ядер (минус запас под ffmpeg).
import { spawn } from 'node:child_process';
import { cpus } from 'node:os';
import { mkdirSync } from 'node:fs';

const OUT = decodeURIComponent(new URL("./out", import.meta.url).pathname);  // готовые фоны
mkdirSync(OUT, { recursive: true });
const JOBS = process.argv.slice(2).length
  ? process.argv.slice(2).map(s => s.split(':'))
  : [['dots'], ['contour'], ['diagonal'], ['blueprint']].flatMap(([s]) => [[s, 'dark'], [s, 'light']]);

const limit = Math.max(1, Math.min(4, Math.floor(cpus().length / 3)));
const queue = [...JOBS];
let failed = 0;

async function worker() {
  for (let job = queue.shift(); job; job = queue.shift()) {
    const [style, mode] = job;
    const out = `${OUT}/${style}-${mode}-loop.mp4`;
    const code = await new Promise(res => {
      const p = spawn('node', ['render.mjs', style, mode, out], { cwd: import.meta.dirname, stdio: 'inherit' });
      p.on('close', res);
    });
    if (code !== 0) { failed++; console.error(`FAILED ${style}/${mode}`); }
  }
}

await Promise.all(Array.from({ length: limit }, worker));
console.log(failed ? `готово, ошибок: ${failed}` : 'готово, все ролики собраны');
process.exit(failed ? 1 : 0);
