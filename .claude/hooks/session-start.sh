#!/bin/bash
# Ставит зависимости Remotion, чтобы в облачной сессии Claude Code сразу можно было рендерить видео.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR/retrograd/remotion"
npm install --no-audit --no-fund
