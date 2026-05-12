#!/usr/bin/env bash
# Local dev backend launcher. Centralizes env so we stop juggling them inline.
set -euo pipefail

cd "$(dirname "$0")/../backend"

export CORS_ALLOW_ORIGIN="http://localhost:5173;http://localhost:8080"
export WEBUI_SECRET_KEY="dev-local-secret-key"
export WEBUI_NAME="思源"
export ENABLE_SIGNUP=true
export SMS_PROVIDER=log

# OpenRouter as unified upstream LLM provider.
export ENABLE_OPENAI_API=true
export ENABLE_OLLAMA_API=false
export OPENAI_API_BASE_URLS="https://openrouter.ai/api/v1"
export OPENAI_API_KEYS="${OPENROUTER_API_KEY:-}"

if [[ -z "${OPENAI_API_KEYS}" ]]; then
  echo "ERROR: OPENROUTER_API_KEY not set" >&2
  exit 1
fi

exec ../.venv/bin/uvicorn open_webui.main:app --port 8080 --host 0.0.0.0 --reload
