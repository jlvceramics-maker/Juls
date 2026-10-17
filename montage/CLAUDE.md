# CLAUDE.md

Монтажерский пак для вертикальных роликов 1080×1920. Подробное описание каждой папки и правила стиля — в `README.md`, читай его перед любой задачей монтажа.

## Окружение

Нужны ffmpeg, Python 3 с `faster-whisper`, Node.js с `playwright-core` и Chrome/Chromium. Если чего-то нет:

```
apt-get install -y ffmpeg || brew install ffmpeg
pip install faster-whisper
npm i playwright-core && npx playwright install chromium
```

`title*.mjs`, `badge.mjs`, `card.mjs` запускаются с `channel: "chrome"`. Если Chrome нет, а есть Chromium от playwright, убери `channel` в `chromium.launch()`.

## Как делать типовые задачи

**Смонтировать говорящую голову с субтитрами.**
1. Создай папку ролика: `reel/inbox/` (исходники), `reel/edit/fonts/ReelSub.ttf` (из `02 Субтитры/`), `reel/scripts/` (скопируй `02 Субтитры/build.py`, `02 Субтитры/transcribe.py`, `03 Заголовки и плашки/title.mjs`).
2. В `build.py` заполни `REELS` и `TITLES`.
3. `python3 reel/scripts/build.py`. Готовое — `reel/edit/out/`.

**Вставить записи экрана в говорящую голову.** Бери `06 Фишки/шаблон b-roll вставок/`, инструкция в его README.

**Подложить фон под графику или запись экрана.** Лупы в `01 Фоны/`, 20 с. Длиннее — зациклить: `ffmpeg -stream_loop -1 -i bg.mp4 -t <сек> ...`.

**Сделать новый фон.** `01 Фоны/генератор bg-lab/`, команды в его README.

## Правила, которые нельзя нарушать

- Паузы резать только от 0.5 с и не в ноль, оставлять около 0.35 с. Нет длинных пауз — не резать.
- Без цветкора и виньетки.
- Субтитры: до 3 слов в строке, активное слово #FFF4A3, y около 1660.
- Заголовок не ниже y 500, иначе закрывает лицо.
- Логотипы сервисов не рисовать руками: брать SVG из `@lobehub/icons-static-svg` или simple-icons.
- Перед отдачей ролика смотреть лист кадров: `ffmpeg -i out.mp4 -vf "fps=1,scale=270:-1,tile=6x4" sheet.png`.
