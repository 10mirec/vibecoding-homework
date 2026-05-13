#!/usr/bin/env bash
# Idempotentný setup pre agent workspace.
# Spusti raz po klonovaní repa. Možno pustiť opakovane — nepoškodí nič.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$WORKSPACE_DIR"

echo "================================================================"
echo " NutriFlow — Bootstrap agent workspace"
echo "================================================================"

echo ""
echo "[1/5] Overujem .mcp.json validitu..."
python3 -m json.tool < .mcp.json > /dev/null
echo "      ✓ .mcp.json je validné JSON"

echo ""
echo "[2/5] Overujem .claude/settings.json validitu..."
python3 -m json.tool < .claude/settings.json > /dev/null
echo "      ✓ settings.json je validné JSON"

echo ""
echo "[3/5] Overujem frontmatter všetkých Skills..."
for f in .claude/skills/*/SKILL.md; do
  if ! head -1 "$f" | grep -q "^---$"; then
    echo "      ✗ BROKEN frontmatter: $f"
    exit 1
  fi
  echo "      ✓ $f"
done

echo ""
echo "[4/5] Overujem frontmatter všetkých Subagentov..."
for f in .claude/agents/*.md; do
  if ! head -1 "$f" | grep -q "^---$"; then
    echo "      ✗ BROKEN frontmatter: $f"
    exit 1
  fi
  echo "      ✓ $f"
done

echo ""
echo "[5/5] Inštalujem dependencies custom MCP servera (rohlik-promo)..."
if command -v uv >/dev/null 2>&1; then
  (cd mcp_servers/rohlik_promo && uv sync --quiet) && echo "      ✓ uv sync hotový"
else
  echo "      ⚠ uv nenájdený, preskakujem MCP server install"
  echo "        Nainštaluj: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

echo ""
echo "================================================================"
echo " ✓ Hotovo. Otvor tento adresár v Claude Code ako workspace."
echo ""
echo "   - CLAUDE.md sa načíta automaticky"
echo "   - /agents príkaz ukáže 8 subagentov"
echo "   - /mcp príkaz ukáže 3 MCP servery"
echo "   - Skill tool má prístup k 3 lokálnym skills"
echo "================================================================"
