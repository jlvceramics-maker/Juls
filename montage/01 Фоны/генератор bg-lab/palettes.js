// Палитры. Каждый стиль живёт в двух версиях: dark и light.
const hex = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16) / 255);

export const STYLE_NAMES = {
  dots:      'Точки',
  contour:   'Изолинии',
  diagonal:  'Диагональ',
  blueprint: 'Миллиметровка',
  dust:      'Пыль',
  silk:      'Складка'
};

export const PALETTES = {
  dots: {
    dark:  { ink: hex('#e6d9c6'), bg1: hex('#141110'), bg2: hex('#1b1614'),
             glowA: [0.30, 0.19, 0.06], glowB: [0.26, 0.09, 0.04], inkAlpha: 0.14, grain: 0.035 },
    light: { ink: hex('#a89a86'), bg1: hex('#f4f1ea'), bg2: hex('#eae5db'),
             glowA: [0.07, 0.05, 0.01], glowB: [0.09, 0.04, 0.02], inkAlpha: 0.30, grain: 0.030 }
  },
  contour: {
    dark:  { ink: hex('#bb8d52'), bg1: hex('#141110'), bg2: hex('#1b1714'),
             glowA: [0.15, 0.10, 0.04], glowB: [0.13, 0.06, 0.03], inkAlpha: 0.24, grain: 0.035 },
    light: { ink: hex('#b48547'), bg1: hex('#f3ece1'), bg2: hex('#e8ded0'),
             glowA: [0.06, 0.04, 0.00], glowB: [0.08, 0.03, 0.01], inkAlpha: 0.28, grain: 0.030 }
  },
  diagonal: {
    dark:  { ink: hex('#f2f2ee'), bg1: hex('#0d0d0c'), bg2: hex('#141412'),
             glowA: [0.11, 0.11, 0.09], glowB: [0.09, 0.07, 0.05], inkAlpha: 0.16, grain: 0.035 },
    light: { ink: hex('#9dbb43'), bg1: hex('#fafaf7'), bg2: hex('#eff0e9'),
             glowA: [0.07, 0.10, 0.02], glowB: [0.05, 0.07, 0.01], inkAlpha: 0.30, grain: 0.028 }
  },
  blueprint: {
    dark:  { ink: hex('#9db4c6'), bg1: hex('#0c0e11'), bg2: hex('#131720'),
             glowA: [0.05, 0.07, 0.10], glowB: [0.05, 0.06, 0.08], inkAlpha: 0.20, grain: 0.032 },
    light: { ink: hex('#7fa3c2'), bg1: hex('#f4f6f8'), bg2: hex('#e8edf2'),
             glowA: [0.03, 0.06, 0.11], glowB: [0.03, 0.05, 0.09], inkAlpha: 0.26, grain: 0.028 }
  },
  dust: {
    dark:  { ink: hex('#f0e6d4'), bg1: hex('#100f0e'), bg2: hex('#181614'),
             glowA: [0.18, 0.12, 0.05], glowB: [0.15, 0.07, 0.03], inkAlpha: 0.18, grain: 0.030 },
    light: { ink: hex('#b3a693'), bg1: hex('#f5f2eb'), bg2: hex('#ebe6db'),
             glowA: [0.06, 0.04, 0.01], glowB: [0.08, 0.03, 0.02], inkAlpha: 0.26, grain: 0.026 }
  },
  silk: {
    dark:  { ink: hex('#d98a5c'), bg1: hex('#141010'), bg2: hex('#1c1614'),
             glowA: [0.22, 0.12, 0.05], glowB: [0.20, 0.07, 0.03], inkAlpha: 0.16, grain: 0.032 },
    light: { ink: hex('#e8a883'), bg1: hex('#f4f0eb'), bg2: hex('#ece5dd'),
             glowA: [0.07, 0.04, 0.01], glowB: [0.09, 0.04, 0.02], inkAlpha: 0.24, grain: 0.026 }
  }
};
