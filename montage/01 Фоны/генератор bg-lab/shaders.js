// Общая база: искажённое пространство + мягкие световые пятна + зерно.
// Движение завязано на PHASE = 2*PI*t/LOOP — луп бесшовный по построению.
export const COMMON = `
precision highp float;
uniform vec2 uRes;
uniform float uPhase;
uniform vec3 uInk;
uniform vec3 uBg1;
uniform vec3 uBg2;
uniform vec3 uGlowA;
uniform vec3 uGlowB;
uniform float uInkAlpha;
uniform float uGrain;

const float PI = 3.14159265359;

float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

float blob(vec2 uv, vec2 c, float r){
  float d = length((uv - c) * vec2(1.0, 0.62));
  return exp(-pow(d / r, 2.0));
}

// ВАЖНО: warp работает в нормализованном пространстве (единицы ~1),
// до умножения на число клеток. Иначе частота волны растёт вместе с сеткой и рвёт её.
vec2 warp(vec2 p, float amp){
  p.x += amp * sin(p.y * 5.2 + uPhase);
  p.y += amp * sin(p.x * 4.1 - uPhase + 1.7);
  p.x += amp * 0.4 * sin(p.y * 9.0 - uPhase * 2.0);
  return p;
}

// квадратное пространство: x 0..1, y 0..aspect
vec2 sq(vec2 uv){ return vec2(uv.x, uv.y * uRes.y / uRes.x); }

float lineMask(float v, float w){
  float d = abs(fract(v) - 0.5);
  return 1.0 - smoothstep(0.0, w, d);
}

vec3 backdrop(vec2 uv){
  vec3 col = mix(uBg1, uBg2, uv.y);
  vec2 ca = vec2(0.74 + 0.06 * sin(uPhase), 0.78 + 0.05 * cos(uPhase));
  vec2 cb = vec2(0.24 + 0.07 * cos(uPhase), 0.28 + 0.05 * sin(uPhase));
  col += uGlowA * blob(uv, ca, 0.36);
  col += uGlowB * blob(uv, cb, 0.40);
  return col;
}

vec3 finish(vec3 col, vec2 uv){
  col += (hash(gl_FragCoord.xy + uPhase) - 0.5) * uGrain;
  float v = 1.0 - 0.16 * pow(length((uv - 0.5) * vec2(1.0, 0.7)) * 1.6, 2.0);
  return clamp(col * v, 0.0, 1.0);
}
`;

export const STYLES = {
  // Пыль: мягкие частицы разного размера, медленный дрейф. Взамен «Развёртки»
  dust: `
    float cell(vec2 uv, vec2 id, float seed){
      vec2 c = fract(vec2(hash(id + seed), hash(id + seed + 7.3)));
      float r = 0.05 + 0.22 * hash(id + seed + 3.1);
      float ph = uPhase + 6.2831 * hash(id + seed + 1.7);
      c += vec2(0.16 * sin(ph), 0.13 * cos(ph));
      float d = length(fract(uv) - c);
      return (1.0 - smoothstep(r * 0.4, r, d)) * (0.35 + 0.65 * hash(id + seed + 9.9));
    }
    void main(){
      vec2 uv = gl_FragCoord.xy / uRes;
      vec2 p = sq(uv) * 6.0;
      vec2 id = floor(p);
      float pat = 0.0;
      for (int j = -1; j <= 1; j++) {
        for (int i = -1; i <= 1; i++) {
          vec2 o = vec2(float(i), float(j));
          pat = max(pat, cell(p - o, id + o, 0.0) );
        }
      }
      vec3 col = backdrop(uv);
      col = mix(col, uInk, pat * uInkAlpha);
      gl_FragColor = vec4(finish(col, uv), 1.0);
    }`,

  // Складка: вертикальные драпировки света, как шёлк. Взамен «Перспективы»
  silk: `
    void main(){
      vec2 uv = gl_FragCoord.xy / uRes;
      vec2 p = sq(uv);
      float f = sin(p.x * 7.0 + sin(p.y * 2.0 + uPhase) * 1.3 + uPhase + 0.9)
              + 0.6 * sin(p.x * 12.0 - sin(p.y * 1.4 - uPhase) * 1.1 - uPhase);
      float pat = 0.5 + 0.5 * sin(f * 1.6);
      pat = pow(pat, 2.2);
      vec3 col = backdrop(uv);
      col = mix(col, uInk, pat * uInkAlpha);
      gl_FragColor = vec4(finish(col, uv), 1.0);
    }`,

  // Точечная сетка: точки дышат на волне, размер зависит от света под ними
  dots: `
    void main(){
      vec2 uv = gl_FragCoord.xy / uRes;
      vec2 p = warp(sq(uv), 0.018) * 13.0;
      float d = length(fract(p) - 0.5);
      float pat = 1.0 - smoothstep(0.10, 0.17, d);
      vec3 col = backdrop(uv);
      col = mix(col, uInk, pat * uInkAlpha);
      gl_FragColor = vec4(finish(col, uv), 1.0);
    }`,

  // Топографические изолинии — медленный дрейф рельефа
  contour: `
    void main(){
      vec2 p = sq(gl_FragCoord.xy / uRes) * 4.2;
      float h = sin(p.x * 1.9 + uPhase) * 0.55
              + sin(p.y * 1.5 - uPhase + 2.4) * 0.55
              + sin((p.x + p.y) * 1.1 + uPhase * 2.0) * 0.35
              + sin((p.x - p.y) * 2.3 - uPhase) * 0.22;
      float pat = lineMask(h * 2.6, 0.10);
      vec3 col = backdrop(gl_FragCoord.xy / uRes);
      col = mix(col, uInk, pat * uInkAlpha);
      gl_FragColor = vec4(finish(col, gl_FragCoord.xy / uRes), 1.0);
    }`,

  // Горизонтальная развёртка: широкие мягкие полосы, слегка изогнутые
  scanlines: `
    void main(){
      vec2 uv = gl_FragCoord.xy / uRes;
      vec2 p = warp(sq(uv), 0.022) * 22.0;
      float pat = lineMask(p.y, 0.30);
      vec3 col = backdrop(uv);
      col = mix(col, uInk, pat * uInkAlpha);
      gl_FragColor = vec4(finish(col, uv), 1.0);
    }`,

  // Только свет: три пятна, ни одной линии. Максимальная читаемость текста поверх
  haze: `
    void main(){
      vec2 uv = gl_FragCoord.xy / uRes;
      vec3 col = backdrop(uv);
      vec2 cc = vec2(0.48 + 0.24 * sin(uPhase), 0.52 + 0.20 * cos(uPhase));
      col += uGlowA * 0.45 * blob(uv, cc, 0.30);
      gl_FragColor = vec4(finish(col, uv), 1.0);
    }`,

  // Пол, уходящий к горизонту; линии медленно едут на зрителя
  perspective: `
    void main(){
      vec2 uv = gl_FragCoord.xy / uRes;
      float horizon = 0.72;
      float depth = horizon - uv.y;
      vec3 col = backdrop(uv);
      if (depth > 0.004) {
        float z = 0.16 / depth;
        float x = (uv.x - 0.5) * z * 2.2;
        float y = z + uPhase / (2.0 * PI) * 3.0;
        float w = clamp(0.02 * z, 0.02, 0.30);
        float pat = max(lineMask(x, w), lineMask(y, w));
        pat *= smoothstep(0.0, 0.22, horizon - uv.y);
        col = mix(col, uInk, pat * uInkAlpha);
      }
      gl_FragColor = vec4(finish(col, uv), 1.0);
    }`,

  // Рябь: кольца от смещающегося источника, гаснут к краям
  ripple: `
    void main(){
      vec2 uv = gl_FragCoord.xy / uRes;
      vec2 p = sq(uv);
      vec2 c = vec2(0.5, 0.5 * uRes.y / uRes.x) + vec2(0.20 * sin(uPhase), 0.26 * cos(uPhase));
      float d = length((p - c) * vec2(1.0, 0.88));
      float pat = lineMask(d * 8.0 - uPhase / (2.0 * PI) * 3.0, 0.22);
      pat *= smoothstep(1.30, 0.10, d);
      vec3 col = backdrop(uv);
      col = mix(col, uInk, pat * uInkAlpha);
      gl_FragColor = vec4(finish(col, uv), 1.0);
    }`,

  // Диагональная сетка 30 градусов, лёгкое дыхание
  diagonal: `
    void main(){
      vec2 uv = gl_FragCoord.xy / uRes;
      vec2 p = warp(sq(uv), 0.014);
      float a = radians(30.0);
      p = mat2(cos(a), -sin(a), sin(a), cos(a)) * p * 9.0;
      float pat = max(lineMask(p.x, 0.055), lineMask(p.y, 0.055));
      vec3 col = backdrop(uv);
      col = mix(col, uInk, pat * uInkAlpha);
      gl_FragColor = vec4(finish(col, uv), 1.0);
    }`,

  // Миллиметровка: мелкая сетка плюс жирная каждые 5 клеток
  blueprint: `
    void main(){
      vec2 uv = gl_FragCoord.xy / uRes;
      vec2 p = warp(sq(uv), 0.010) * 20.0;
      float fine = max(lineMask(p.x, 0.055), lineMask(p.y, 0.055));
      float bold = max(lineMask(p.x / 5.0, 0.012), lineMask(p.y / 5.0, 0.012));
      vec3 col = backdrop(uv);
      col = mix(col, uInk, fine * uInkAlpha * 0.40);
      col = mix(col, uInk, bold * uInkAlpha);
      gl_FragColor = vec4(finish(col, uv), 1.0);
    }`
};
