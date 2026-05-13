# Príklad 03 — MCP Tool Call

> Ako Claude Code volá custom MCP server (`rohlik-promo`) v stdio mode a využije výstup pre debug fallback flow.

## Scenár

Užívateľ má sťažnosť: „Shopper agent v testoch nezvláda Rohlik failure — workflow padá namiesto fallback path."

## Konverzácia

### 👤 Užívateľ

> Shopper má padať gracefully ak Rohlik MCP zlyhá. V integration teste však workflow končí 500-kou. Skontroluj prečo.

### 🤖 Claude

> Routing tabuľka: úloha „Rohlik MCP debug" → subagent `mcp-integrator`, MCP `rohlik-promo`. Najprv overím že MCP server funguje a viem dosiahnuť mock_failure mode.

> Zavolám tool `get_status()` z custom MCP servera:

```
mcp__rohlik-promo__get_status()

→ ServerStatus(status='ok', mode='mock_success', version='0.1.0')
```

> Server beží v `mock_success`. Pre debug fallback path potrebujem **mock_failure**. Reštartnem server s iným env var (alebo zmením `.mcp.json`).

> Pre teraz použijem manuálny invoke s `mock_failure` mode (v reálnom CI sa to robí cez env override):

```
ROHLIK_MCP_MODE=mock_failure uv run python homework/mcp_servers/rohlik_promo/server.py
```

> Skontrolujem ako `get_promotions()` reaguje:

```
mcp__rohlik-promo__get_promotions()

→ Error: RuntimeError("Rohlik MCP nedostupný (mock_failure mode).
                       Shopper agent musí pokračovať s prázdnym PromotionContext.")
```

> Toto je očakávané. Teraz `sync_cart`:

```
mcp__rohlik-promo__sync_cart(items=[{name: "ryza", quantity: 1, unit: "kg"}])

→ CartSyncResult(
    status='failed',
    cart_url=None,
    message_cs='Cart sync zlyhal (mock_failure mode). Užívateľ dostane shopping list bez Rohlik košíka.'
  )
```

> MCP server správne signalizuje zlyhanie. Teraz dispatch `mcp-integrator` aby skontroloval ako backend adapter reaguje:

### Dispatch subagent

```
[Agent dispatch] mcp-integrator:
  Task: "Debug Shopper fallback flow.
         Reprodukcia: ROHLIK_MCP_MODE=mock_failure spustí workflow,
         get_promotions() raises RuntimeError. Backend ho má zachytiť
         ako MCPUnavailable a Shopper má dostať prázdny PromotionContext.
         Skontroluj backend/src/nutriflow/tools/rohlik_mcp.py:
         1. Try/except okolo MCP volaní
         2. Mapping RuntimeError → MCPUnavailable
         3. Shopper agent v recon vracia empty context, nie raise
         MCP tool rohlik-promo môžeš použiť aj počas debug pre re-test."
```

### 🔧 Subagent `mcp-integrator`

```
[reading backend/src/nutriflow/tools/rohlik_mcp.py]

  Nájdený problém: try/except chyta MCPUnavailable, ale custom
  rohlik-promo MCP server raisuje generický RuntimeError.
  Adapter musí mapovať na MCPUnavailable.

[editing rohlik_mcp.py: pridáva except (MCPUnavailable, RuntimeError)]

[reading tests/integration/test_rohlik_fallback.py — regression test]
[running uv run pytest tests/integration/test_rohlik_fallback.py -v]

  PASSED ✓ — workflow končí s shopping_list, status='failed', warning v _cs

[volá MCP rohlik-promo znova pre confirmation]
mcp__rohlik-promo__get_promotions()
→ RuntimeError (caught a mapnutý správne)
✓ done.
```

### 🤖 Claude (späť)

> Fix-nuté. Root cause: backend adapter chytal iba `MCPUnavailable`, ale custom `rohlik-promo` MCP server vyhadzuje `RuntimeError`. Pridali sme aj `RuntimeError` do except sekcie. Integration test prešiel.

> Custom MCP server `rohlik-promo` slúžil v tomto procese ako **reálny live source of failure** — bez neho by sme len špekulovali, ako Rohlik failure vyzerá. MCP tools sú dôležitejšie ako mockovaný adapter, lebo bežia v rovnakom JSON-RPC protokole ako produkčné MCP servery.

---

## Čo ukazuje tento príklad

1. **Custom MCP server slúži ako reálny debug nástroj** — nielen showcase pre kurzové zadanie, ale produkčne použiteľný počas debugu.
2. **Stdio protocol funguje cez Claude Code** — server beží ako child process, komunikuje cez stdin/stdout JSON-RPC.
3. **Mode switching cez env** — `ROHLIK_MCP_MODE` prepína mock_success ↔ mock_failure bez code change.
4. **MCP server typed payloads** — Pydantic schémy (`CartSyncResult`, `PromotionContext`) sú zarovnané s backend domain schemami → ID schémy nevypadne pri MCP boundary.
5. **MCP + subagent + (žiadny skill)** — táto úloha bola pure plumbing, žiadny skill jej nepasoval (skill `mcp-fallback-design` by sme mohli pridať, ale pre MVP nebolo nutné).

## Súbory dotknuté

- `backend/src/nutriflow/tools/rohlik_mcp.py` (rozšírený except)
- `backend/tests/integration/test_rohlik_fallback.py` (test prešiel)
