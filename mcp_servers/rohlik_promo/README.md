# rohlik-promo MCP Server

Vlastný MCP stdio server emulujúci Rohlik akcie a cart sync. Slúži ako demoštračný príklad **postavenia vlastného MCP servera** pre NutriFlow homework.

## Tools

| Tool | Vstup | Výstup | Účel |
|---|---|---|---|
| `get_promotions()` | — | `PromotionContext` | Vráti zoznam akcií, ktoré Shopper agent dostane v recon fáze |
| `sync_cart(items)` | `list[CartItem]` | `CartSyncResult` | Mock sync shopping listu do Rohlik košíka |
| `get_status()` | — | `ServerStatus` | Health check |

Všetky payloady sú **typed Pydantic v2** — zarovnané s `backend/src/nutriflow/domain/schemas.py` v hlavnom NutriFlow projekte.

## Inštalácia

```bash
cd /workspaces/NutriFlow/homework/mcp_servers/rohlik_promo
uv sync
```

To vytvorí lokálny `.venv` a nainštaluje `mcp[cli]` + `pydantic`.

## Spustenie (manuálne testovanie)

```bash
uv run python server.py
```

Server čaká na stdin MCP messages (JSON-RPC over stdio). Pre realisticky test použiť MCP Inspector:

```bash
npx @modelcontextprotocol/inspector uv run python server.py
```

Otvorí webové UI kde môžeš invokovať tools.

## Integrácia s Claude Code

Server je registrovaný v [`../../.mcp.json`](../../.mcp.json):

```json
{
  "rohlik-promo": {
    "command": "uv",
    "args": ["run", "--directory", "/workspaces/NutriFlow/homework/mcp_servers/rohlik_promo", "python", "server.py"],
    "env": {"ROHLIK_MCP_MODE": "mock_success"}
  }
}
```

Claude Code pri otvorení `homework/` workspace automaticky spustí tento server v stdio mode a exposuje 3 tools pod menom `mcp__rohlik-promo__*`.

## Demo modes

| Mode | Správanie |
|---|---|
| `ROHLIK_MCP_MODE=mock_success` (default) | Všetky tools vrátia OK |
| `ROHLIK_MCP_MODE=mock_failure` | `get_promotions()` vyhodí `RuntimeError`, `sync_cart()` vráti `status="failed"` |

`mock_failure` slúži na demoštráciu **fallback flow**: Shopper agent musí zvládnuť zlyhanie MCP a workflow musí dobehnúť so shopping listom bez cart syncu.

## Architektúra

Server používa **FastMCP** z oficiálneho `mcp` Python SDK:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("rohlik-promo")

@mcp.tool()
def get_promotions() -> PromotionContext:
    ...
```

FastMCP automaticky:
- Generuje JSON schema z Pydantic type hints
- Validuje vstupy/výstupy
- Komunikuje cez stdio MCP protocol

## Súvisiace súbory

- [`server.py`](server.py) — kód MCP servera
- [`pyproject.toml`](pyproject.toml) — uv dependencies
- [`../../.mcp.json`](../../.mcp.json) — registrácia v Claude Code
- [`../../CLAUDE.md`](../../CLAUDE.md) — routing tabuľka (`rohlik-promo` stĺpec)
- [`../../.claude/agents/mcp-integrator.md`](../../.claude/agents/mcp-integrator.md) — subagent, ktorý tento server primárne používa
- Backend NutriFlow analóg (Python adapter, nie MCP server): `backend/src/nutriflow/tools/rohlik_mcp.py`

## Prečo vlastný MCP server (a nie iba reuse `postgres`/`filesystem`)

Tým ukazujeme, že vieme MCP **nielen použiť**, ale aj **postaviť**. Pre kurzové zadanie je to dôležitý signál — student demonštruje hlbšie pochopenie protokolu.

Server je úmyselne **mock-only** (žiadne reálne Rohlik HTTPS) — produkčná verzia by:
1. Mala HTTPS klienta (`httpx`).
2. Načítavala API key z env (`ROHLIK_API_TOKEN`).
3. Volala reálny `GET /v2/products/promotions` endpoint.
4. Mapovala odpoveď do tej istej `PromotionContext` schémy.

Boundary medzi MCP tool a backend logikou by zostal rovnaký — to je hodnota typed Pydantic schém.
