#!/usr/bin/env bash
set -euo pipefail
command -v npm >/dev/null || { echo 'Install Node.js 22 and npm first'; exit 1; }
mkdir -p .tools/bin
if [ ! -x .tools/agent-venv/bin/python3 ]; then
  python3 -m venv .tools/agent-venv
fi
.tools/agent-venv/bin/pip install uv==0.13.6
if [ "${1:-}" != "--renderer-only" ]; then
  npm install --prefix .tools/agent --no-audit --no-fund @openai/codex@0.164.0
fi
ln -sf "$PWD/.tools/agent-venv/bin/uv" .tools/bin/uv
printf 'export PATH="%s/.tools/bin:%s/.tools/agent/node_modules/.bin:$PATH"\n' "$PWD" "$PWD" > .tools/agent.env
