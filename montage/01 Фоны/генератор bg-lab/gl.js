import { COMMON, STYLES } from './shaders.js';

const VERT = `attribute vec2 a; void main(){ gl_Position = vec4(a, 0.0, 1.0); }`;

function compile(gl, type, src) {
  const s = gl.createShader(type);
  gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
  return s;
}

export function createRenderer(canvas, styleKey, palette) {
  const gl = canvas.getContext('webgl', { preserveDrawingBuffer: true, antialias: false });
  if (!gl) throw new Error('no webgl');
  const prog = gl.createProgram();
  gl.attachShader(prog, compile(gl, gl.VERTEX_SHADER, VERT));
  gl.attachShader(prog, compile(gl, gl.FRAGMENT_SHADER, COMMON + STYLES[styleKey]));
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
  gl.useProgram(prog);

  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 3,-1, -1,3]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(prog, 'a');
  gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

  const u = n => gl.getUniformLocation(prog, n);
  gl.uniform2f(u('uRes'), canvas.width, canvas.height);
  gl.uniform3fv(u('uInk'), palette.ink);
  gl.uniform3fv(u('uBg1'), palette.bg1);
  gl.uniform3fv(u('uBg2'), palette.bg2);
  gl.uniform3fv(u('uGlowA'), palette.glowA);
  gl.uniform3fv(u('uGlowB'), palette.glowB);
  gl.uniform1f(u('uInkAlpha'), palette.inkAlpha);
  gl.uniform1f(u('uGrain'), palette.grain);
  const uPhase = u('uPhase');

  return function draw(phase) {
    gl.uniform1f(uPhase, phase);
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  };
}
