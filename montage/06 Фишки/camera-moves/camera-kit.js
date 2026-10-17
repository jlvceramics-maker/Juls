// camera-kit.js. Операторская грамматика для анимации кодом (Three.js + Canvas 2D).
// Камера: THREE.PerspectiveCamera с rotation.order 'YXZ'. Метры и градусы.
// Герой в начале координат лицом к +z, камера по умолчанию в (0, 1.5, 10) смотрит вдоль -z.

// ---------- математика ----------
export const TAU = Math.PI * 2;
export const clamp01 = (x) => Math.max(0, Math.min(1, x));
export const lerp = (a, b, k) => a + (b - a) * k;
export const ease = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2); // in-out cubic
export const easeOut = (x) => 1 - Math.pow(1 - clamp01(x), 3);
export const smooth = (a, b, x) => { const k = clamp01((x - a) / (b - a)); return k * k * (3 - 2 * k); };
export const seg = (t, a, b, fn = ease) => fn(clamp01((t - a) / (b - a)));          // прогресс 0..1 на отрезке
export const logLerp = (a, b, k) => Math.exp(lerp(Math.log(a), Math.log(b), k));    // зум, кран, большой наезд
export const rad = (d) => (d * Math.PI) / 180;
export const deg = (r) => (r * 180) / Math.PI;
export const fovOf = (mm, k = 6.9) => deg(2 * Math.atan(k / mm));                    // 24 мм → 32°
export const mmOf = (fov, k = 6.9) => k / Math.tan(rad(fov) / 2);
export const hfovOf = (vfov, aspect) => deg(2 * Math.atan(aspect * Math.tan(rad(vfov) / 2)));
export function rng(seed) { // mulberry32
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
export const num = (v, d = 1) => v.toFixed(d).replace('.', ',');                    // «1,7» для показаний
export const signed = (v) => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v);

// ---------- петля демо ----------
export function loopPhase(t, { period = 4.7, hold = 0.8, move = 2.0, fade = 0.5 } = {}) {
  const lt = ((t % period) + period) % period;
  return { lt, k: seg(lt, hold, hold + move), fadeK: fade ? smooth(period - fade, period, lt) : 0 };
}

// ---------- риги камеры: ставят камеру по прогрессу k или времени t и возвращают показание ----------
const setPos = (cam, p) => cam.position.set(p[0], p[1], p[2]);
const look = (cam, p) => cam.lookAt(p[0], p[1], p[2]);
export const rigs = {
  pan(cam, k, { from = -18, to = 18, pos = [0, 1.5, 10] } = {}) {             // 01
    const a = lerp(from, to, k); setPos(cam, pos); cam.rotation.set(0, rad(-a), 0, 'YXZ'); return `${signed(Math.round(a))}°`;
  },
  tilt(cam, k, { from = -3, to = 21, pos = [0, 1.2, 7.5] } = {}) {            // 02
    const a = lerp(from, to, k); setPos(cam, pos); cam.rotation.set(rad(a), 0, 0, 'YXZ'); return `${signed(Math.round(a))}°`;
  },
  dolly(cam, k, { from = 10, to = 2.6, height = 1.45, mm = 24 } = {}) {        // 03
    setPos(cam, [0, height, lerp(from, to, k)]); cam.rotation.set(0, 0, 0, 'YXZ'); cam.fov = fovOf(mm); return `${mm} мм`;
  },
  zoom(cam, k, { from = 24, to = 87, pos = [0, 1.45, 10] } = {}) {             // 04
    const mm = logLerp(from, to, k); setPos(cam, pos); cam.rotation.set(0, 0, 0, 'YXZ'); cam.fov = fovOf(mm); return `${Math.round(mm)} мм`;
  },
  tracking(cam, x, { dist = 7.6, height = 1.5, lead = 0, speed = 1.7 } = {}) { // 05, x героя задает сцена
    setPos(cam, [x + lead, height, dist]); cam.rotation.set(0, 0, 0, 'YXZ'); return `→ ${num(speed)} м/с`;
  },
  orbit(cam, k, { from = -54, to = 54, radius = 6.2, height = 1.75, target = [0, 1.05, 0] } = {}) { // 06
    const a = lerp(from, to, k);
    setPos(cam, [target[0] + Math.sin(rad(a)) * radius, height, target[2] + Math.cos(rad(a)) * radius]); look(cam, target);
    return `${signed(Math.round(a))}°`;
  },
  crane(cam, k, { from = 1.4, to = 9, dist = 8, target = [0, 0.9, 0] } = {}) { // 07
    const h = logLerp(from, to, k); setPos(cam, [target[0], h, target[2] + dist]); look(cam, target); return `↑ ${num(h)} м`;
  },
  dollyZoom(cam, k, { fromMm = 10, toMm = 24, d0 = 4.2, height = 1.5 } = {}) { // 08, d = d0 · f / f0
    const mm = lerp(fromMm, toMm, k);
    cam.fov = fovOf(mm); setPos(cam, [0, height, d0 * mm / fromMm]); cam.rotation.set(0, 0, 0, 'YXZ'); return `${Math.round(mm)} мм`;
  },
  handheld(cam, t, { loop = 4.7, pos = [0, 1.5, 10], amp = 1 } = {}) {         // 10, кратные частоты дают петлю без шва
    const w = TAU / loop, n = (list) => list.reduce((s, [a, m, p]) => s + a * Math.sin(w * m * t + p), 0) * amp;
    cam.position.set(pos[0] + n([[0.03, 3, 0.2], [0.015, 7, 1.1]]), pos[1] + n([[0.02, 5, 2.1], [0.01, 11, 0.4]]), pos[2]);
    cam.rotation.set(rad(n([[0.45, 4, 0.7], [0.2, 9, 2.2]])), rad(n([[0.55, 3, 1.4], [0.25, 8, 0.1]])), rad(n([[0.6, 2, 0.3], [0.25, 7, 1.9]])), 'YXZ');
    return 'С РУК';
  },
  fpv(cam, t, { speed = 13.9, start = [0, 2.2, 34], weave = 1.4, freq = 1.35, roll = 0.34, pitch = -4 } = {}) { // 11
    cam.position.set(start[0] + weave * Math.sin(t * freq), start[1] + 0.5 * Math.sin(t * 0.9), start[2] - speed * t);
    cam.rotation.set(rad(pitch + 3 * Math.sin(t * 0.9 + 1)), -0.16 * Math.cos(t * freq), roll * Math.sin(t * freq + 0.5), 'YXZ');
    return `${Math.round(speed * 3.6)} км/ч`;
  },
  dutch(cam, k, { to = 21, pos = [0, 1.5, 10] } = {}) {                         // 12
    const a = lerp(0, to, k); setPos(cam, pos); cam.rotation.set(0, 0, rad(a), 'YXZ'); return `∠ ${Math.round(a)}°`;
  },
};

// ---------- сюжетное время: слоумо, спидрамп, стоп-кадр ----------
// segments по порядку: { until, rate } держит скорость, { until, to } плавно меняет ее к to, последний без until
export function piecewiseRate(segments) {
  return (u) => {
    let prevEnd = 0, prevRate = segments[0].rate ?? 1;
    for (const s of segments) {
      const end = s.until ?? Infinity;
      if (u < end) return s.to != null ? lerp(prevRate, s.to, smooth(prevEnd, end, u)) : s.rate;
      prevRate = s.to ?? s.rate; prevEnd = end;
    }
    return prevRate;
  };
}
// story(u) сюжетное время, real(s) реальное время, когда сюжет дошел до s
export function makeStoryTime(rate, { until = 30, dt = 0.002 } = {}) {
  const n = Math.ceil(until / dt), acc = new Float64Array(n + 1);
  for (let i = 1; i <= n; i++) acc[i] = acc[i - 1] + rate((i - 0.5) * dt) * dt;
  const story = (u) => { const f = Math.max(0, Math.min(n, u / dt)), i = Math.floor(f); return acc[i] + (acc[Math.min(n, i + 1)] - acc[i]) * (f - i); };
  const real = (s) => { let lo = 0, hi = n; while (lo < hi) { const m = (lo + hi) >> 1; if (acc[m] < s) lo = m + 1; else hi = m; } return lo * dt; };
  return { story, rate, real };
}

// ---------- переходы ----------
export const jumpIndex = (t, count, step) => Math.min(count - 1, Math.floor(t / step));          // 17
export function whip(u, { start = 0.2, dur = 0.6, angle = 40, blur = 60 } = {}) {                // 19
  const half = dur / 2;
  if (u < start) return { side: 'from', yaw: 0, hblur: 0 };
  if (u < start + half) { const k = Math.pow((u - start) / half, 2); return { side: 'from', yaw: -angle * k, hblur: blur * k }; }
  if (u < start + dur) { const k = 1 - Math.pow(1 - (u - start - half) / half, 2); return { side: 'to', yaw: angle * (1 - k), hblur: blur * (1 - k) }; }
  return { side: 'to', yaw: 0, hblur: 0 };
}
export const dissolve = (u, { start = 1.0, dur = 1.2 } = {}) => seg(u, start, start + dur);      // 20
export const wipeX = (u, width, { start = 1.0, dur = 1.1 } = {}) => seg(u, start, start + dur) * width; // 21
export const jCut = (cut, lead = 0.45) => ({ audioStart: cut - lead });                          // 23
export const lCut = (cut, tail = 0.4) => ({ audioEnd: cut + tail });                             // 24

// ---------- компоновщик проходов сцены ----------
// renderer: { preserveDrawingBuffer: true, alpha: true }, pixelRatio 1, холст размером с ctx.canvas.
// shot(setup, o): reset() → setup(camera, scene) → рендер → размытие или смаз → прозрачность и обрезка → в ctx.
//   o.alpha (наплыв), o.blur px (перевод фокуса), o.hblur px (переброска), o.transparent (слой без фона),
//   o.rect {x,y,w,h} (часть холста), o.clip {x,y,w,h} (шторка).
// Возвращает project(x, y, z) → {x, y} в пикселях холста для 2D-оверлеев.
export function makeCompositor({ THREE, renderer, scene, camera, ctx, reset = () => {} }) {
  const W = ctx.canvas.width, H = ctx.canvas.height, gl = renderer.domElement;
  const tmp = document.createElement('canvas'); tmp.width = W; tmp.height = H;
  renderer.setScissorTest(true);
  function shot(setup, o = {}) {
    const r = o.rect || { x: 0, y: 0, w: W, h: H };
    reset();
    camera.aspect = r.w / r.h;
    if (setup) setup(camera, scene);
    camera.updateProjectionMatrix(); camera.updateMatrixWorld();
    const glY = H - r.y - r.h;
    renderer.setViewport(r.x, glY, r.w, r.h); renderer.setScissor(r.x, glY, r.w, r.h);
    const bg = scene.background;
    if (o.transparent) { scene.background = null; renderer.setClearColor(0x000000, 0); }
    else renderer.setClearColor(bg && bg.isColor ? bg : 0xffffff, 1);
    renderer.clear(); renderer.render(scene, camera);
    scene.background = bg;
    const t = tmp.getContext('2d');
    t.setTransform(1, 0, 0, 1, 0, 0); t.globalAlpha = 1; t.filter = 'none'; t.clearRect(0, 0, W, H);
    if (o.hblur > 0.5) {
      const n = 16;
      for (let i = 0; i < n; i++) { t.globalAlpha = 1 / (i + 1); t.drawImage(gl, r.x, r.y, r.w, r.h, r.x + (i / (n - 1) - 0.5) * o.hblur, r.y, r.w, r.h); }
      t.globalAlpha = 1;
    } else {
      if (o.blur) t.filter = `blur(${o.blur.toFixed(2)}px)`;
      t.drawImage(gl, r.x, r.y, r.w, r.h, r.x, r.y, r.w, r.h); t.filter = 'none';
    }
    const c = o.clip || r;
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.beginPath(); ctx.rect(c.x, c.y, c.w, c.h); ctx.clip();
    ctx.globalAlpha = o.alpha ?? 1; ctx.drawImage(tmp, 0, 0);
    ctx.restore();
    const vm = camera.matrixWorldInverse.clone(), pm = camera.projectionMatrix.clone();
    return (x, y, z) => { const v = new THREE.Vector3(x, y, z).applyMatrix4(vm).applyMatrix4(pm); return { x: r.x + (v.x + 1) / 2 * r.w, y: r.y + (1 - v.y) / 2 * r.h }; };
  }
  return { shot, W, H };
}

// растворение петли в начало: draw(lt, ctx) рисует кадр в момент lt и возвращает его показания
export function makeLoopFader(W, H) {
  const mk = () => { const c = document.createElement('canvas'); c.width = W; c.height = H; return c; };
  const a = mk(), b = mk();
  return (t, { period = 4.7, fade = 0.5 }, draw, out) => {
    const lt = ((t % period) + period) % period;
    if (!fade || lt < period - fade) return draw(lt, out);
    const resA = draw(lt, a.getContext('2d')), resB = draw(0, b.getContext('2d'));
    const k = smooth(period - fade, period, lt);
    out.save(); out.setTransform(1, 0, 0, 1, 0, 0); out.globalAlpha = 1; out.drawImage(a, 0, 0); out.globalAlpha = k; out.drawImage(b, 0, 0); out.restore();
    return k > 0.35 ? resB : resA; // цифры сразу из начала петли
  };
}
