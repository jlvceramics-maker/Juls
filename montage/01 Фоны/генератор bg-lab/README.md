# bg-lab — генератор видео-подложек для рилсов

Собирает бесшовные луп-подложки 1080×1920, 20 с, 30 fps. Картинка считается
фрагментным шейдером в WebGL, кадры снимаются headless-Chrome через playwright-core
и уходят в ffmpeg через stdin. Промежуточные PNG на диск не пишутся.

## Команды

Один ролик:

    node render.mjs <style> <dark|light> out.mp4

Все ролики разом (кладёт в `public/backgrounds/`):

    node batch.mjs

Выборочно:

    node batch.mjs dots:dark contour:light

Контактный лист всех стилей в обеих палитрах:

    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
      --headless --disable-gpu --use-angle=swiftshader --enable-unsafe-swiftshader \
      --allow-file-access-from-files --hide-scrollbars --virtual-time-budget=6000 \
      --window-size=1260,830 --screenshot=contact.png \
      "file://$PWD/contact.html"

## Файлы

- `shaders.js` — общая база (свет, искажение, зерно) плюс тело каждого стиля
- `palettes.js` — цвета, по две палитры на стиль: `dark` и `light`
- `gl.js` — компиляция шейдера и передача uniform-ов
- `frame.html` — страница на один кадр, дёргается из render.mjs через `window.__draw(phase)`
- `contact.html` — сетка превью для выбора глазами
- `render.mjs` / `batch.mjs` — рендер
- `checkloop.mjs` — проверка бесшовности лупа

## Как добавить стиль

1. Новый ключ в `STYLES` внутри `shaders.js`. Тело — обычный `main()`, доступны
   `backdrop(uv)`, `finish(col, uv)`, `warp(p, amp)`, `sq(uv)`, `lineMask(v, w)`.
2. Пара палитр в `PALETTES` и подпись в `STYLE_NAMES` внутри `palettes.js`.
3. Прогнать контактный лист, посмотреть глазами, потом `node batch.mjs <style>:dark <style>:light`.

## Проверка бесшовности

    node checkloop.mjs dots:dark contour:light

Рендерит кадр при фазе 0 и при фазе 2PI с выключенным зерном и сравнивает по PSNR.
Кадры обязаны совпасть: 60 дБ и выше — норма (в реальности выходит 94-110 дБ,
разница только в младшем бите). Ниже 60 дБ означает, что какое-то движение
непериодично и стык лупа будет видно. Для калибровки: подстановка непериодичного
множителя фазы роняет метрику до 28-33 дБ.

## Правило бесшовного лупа

Единственный источник времени — uniform `uPhase`, он пробегает ровно `0..2PI` за
цикл. Любое движение обязано быть периодичным по этой фазе: `sin(x + uPhase)`
годится, `sin(x + uPhase * 1.3)` рвёт стык. Если нужно движение быстрее — умножай
фазу на целое: `uPhase * 2`, `uPhase / (2*PI) * 3`.

Проверяй через `checkloop.mjs`, а не по готовому mp4: у собранного ролика стык
всегда выглядит хуже внутренних переходов из-за кодека (кадр 0 опорный, 599
максимально сжатый), и это маскирует реальную ошибку.

## Ограничения

Рендер идёт на программном OpenGL (swiftshader), один ролик — около четырёх минут.
`batch.mjs` гонит по три-четыре параллельно.
