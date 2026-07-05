#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# setup_ai_keys.sh — Configure DashScope API keys for AI provider rotation
#
# Usage:
#   ./scripts/setup_ai_keys.sh                          # interactive prompt
#   ./scripts/setup_ai_keys.sh --list                   # list current keys
#   ./scripts/setup_ai_keys.sh KEY1 KEY2                # set keys directly
#
# Reads from ~/.env or ./.env and updates DASHSCOPE_API_KEY + DASHSCOPE_API_KEYS
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"

echo "🔑 LMView — AI Key Setup"
echo "========================"
echo ""

# ── Find existing keys ─────────────────────────────────────────────────────

current_single=$(grep -oP '^DASHSCOPE_API_KEY=\K.*' "${ENV_FILE}" 2>/dev/null || echo "")
current_multi=$(grep -oP '^DASHSCOPE_API_KEYS=\K.*' "${ENV_FILE}" 2>/dev/null || echo "")

echo "📋 Current keys in ${ENV_FILE}:"
echo "   DASHSCOPE_API_KEY:   ${current_single:0:20}...${current_single: -8} (${#current_single} chars)"
echo "   DASHSCOPE_API_KEYS:  ${current_multi:0:20}...${current_multi: -8} (${#current_multi} chars)"
echo ""

# ── Handle --list ──────────────────────────────────────────────────────────

if [[ "${1:-}" == "--list" ]]; then
  exit 0
fi

# ── Interactive or direct ──────────────────────────────────────────────────

if [[ $# -ge 1 ]]; then
  KEYS=("$@")
else
  echo "Paste your DashScope API keys (one per line, Ctrl+D when done):"
  echo ""
  mapfile -t KEYS
fi

if [[ ${#KEYS[@]} -eq 0 ]]; then
  echo "❌ No keys provided. Aborting."
  exit 1
fi

SINGLE="${KEYS[0]}"
JOINED=""

for key in "${KEYS[@]}"; do
  key="$(echo "$key" | xargs)"  # trim whitespace
  if [[ -z "$key" ]]; then continue; fi
  if [[ -z "$JOINED" ]]; then
    JOINED="$key"
  else
    JOINED="${JOINED},${key}"
  fi
done

if [[ -z "$JOINED" ]]; then
  echo "❌ No valid keys found."
  exit 1
fi

# ── Update .env ────────────────────────────────────────────────────────────

# Update DASHSCOPE_API_KEY (first key)
if grep -q '^DASHSCOPE_API_KEY=' "${ENV_FILE}" 2>/dev/null; then
  sed -i "s|^DASHSCOPE_API_KEY=.*|DASHSCOPE_API_KEY=${SINGLE}|" "${ENV_FILE}"
else
  echo "DASHSCOPE_API_KEY=${SINGLE}" >> "${ENV_FILE}"
fi

# Update DASHSCOPE_API_KEYS (all keys)
if grep -q '^DASHSCOPE_API_KEYS=' "${ENV_FILE}" 2>/dev/null; then
  sed -i "s|^DASHSCOPE_API_KEYS=.*|DASHSCOPE_API_KEYS=${JOINED}|" "${ENV_FILE}"
else
  echo "DASHSCOPE_API_KEYS=${JOINED}" >> "${ENV_FILE}"
fi

echo ""
echo "✅ Keys updated in ${ENV_FILE}"
echo "   DASHSCOPE_API_KEY:   ${SINGLE:0:20}...${SINGLE: -8}"
echo "   DASHSCOPE_API_KEYS:  ${#KEYS[@]} keys set"
echo ""
echo "To deploy, run:"
echo "   bash scripts/deploy_aws_swarm.sh"
echo ""
echo "The ai-service container will pick up both keys for rotation."
