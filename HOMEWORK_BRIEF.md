# HOMEWORK_BRIEF.md — Zadanie a splnenie

## Pôvodné zadanie

> **Tvé zadání zní:**
> 👉 Nastavení kódovacího Agenta
> 📍 Nasdílejte nastavení Vašeho kódovacího agenta, využijte **MCP Servery, Skilly, Subagenty**.
> **NEPOUŽÍVEJTE PLUGINS ANI MARKETPLACE!**
>
> **Kódovací agenti:**
> - Codex
> - Claude Code
>
> 📄 **Formát:** Vypracovaný úkol odevzdejte ve formě souborů, ideálně nahraných na Github. Můžete nahrát buď zip adresářové struktury projektu, nebo link na Github.

## Zvolená platforma

**Claude Code** — postavené nad ňou je celé NutriFlow.

## Ako je zadanie splnené

### ✅ MCP Servery

Tri MCP servery konfigurované v [.mcp.json](.mcp.json):

| Server | Pôvod | Účel |
|---|---|---|
| `postgres` | verejný npm balík `@modelcontextprotocol/server-postgres` | Live introspekcia NutriFlow DB schémy + query overovanie |
| `filesystem` | verejný npm balík `@modelcontextprotocol/server-filesystem` | Súborové operácie mimo workspace |
| `rohlik-promo` | **vlastný** Python MCP server (FastMCP, stdio) | Mock Rohlik akcií + cart sync pre Shopper agent integráciu |

**Custom server** v [mcp_servers/rohlik_promo/](mcp_servers/rohlik_promo/) je plnohodnotný MCP stdio server, ktorý:
- Importuje doménové Pydantic schémy z `backend/src/nutriflow/domain/schemas.py` (typed payloads)
- Exposuje 3 tools (`get_promotions`, `sync_cart`, `get_status`)
- Reaguje na `ROHLIK_MCP_MODE` env (`mock_success` / `mock_failure`) — demonstrácia fallback flow

### ✅ Skills

Tri **lokálne** Skills v [.claude/skills/](.claude/skills/) (každý ako `<name>/SKILL.md` s YAML frontmatter):

| Skill | Doména | Kedy sa aktivuje |
|---|---|---|
| `czech-llm-output` | LLM prompt engineering | Pri písaní/revízii českých LLM promptov a výstupov |
| `agent-handoff-contracts` | Typed data contracts | Pri dizajne Pydantic schém medzi agentmi |
| `pantry-first-meal-planning` | Doménový princíp | Pri práci na Chef agentovi (musí preferovať pantry) |

**Žiadne pluginy, žiadny marketplace.** Nemáme `enabledPlugins` v `settings.json`. Všetky skills sú **statické súbory** v repe.

### ✅ Subagenty

8 subagentov v [.claude/agents/](.claude/agents/):

| Subagent | Doména |
|---|---|
| `backend-architect` | FastAPI skeleton, Docker, Alembic init |
| `db-modeler` | SQLAlchemy modely, migrácie, seed |
| `schema-designer` | Pydantic v2 domain schemas |
| `agent-sdk-builder` | Runtime LLM agenti (Orchestrator/Nutritionist/Chef/Shopper/Critic) |
| `prompt-engineer-cs` | České LLM prompty |
| `mcp-integrator` | Rohlik MCP adapter v backende |
| `frontend-builder` | Next.js 15 + shadcn/ui + zod |
| `test-writer` | pytest + Playwright |

Každý subagent má **YAML frontmatter** (Claude Code formát: `name`, `description`, `tools`, `model`) a explicitnú sekciu `## Skills a MCP, ktoré máš k dispozícii` ktorá ho prepojí s relevantnými skills/MCP servermi.

### ✅ Žiadne pluginy ani marketplace

[.claude/settings.json](.claude/settings.json) neobsahuje `enabledPlugins` ani referencie na marketplace. Iba:
- `permissions.allow` — granted bash patterns
- `env` — locale + MCP mode
- `hooks` — PostToolUse logging bonus (mimo zadania)

`grep -r "plugin" homework/` vráti iba dokumentačné zmienky o tom, že **pluginy NEpoužívame** (napr. v tomto súbore).

### ✅ Orchestrátor (lepidlo)

[CLAUDE.md](CLAUDE.md) je `★` súbor — **Claude Code ho automaticky načítava pri otvorení workspace**. Obsahuje:
- Routing tabuľku „úloha → subagent + skill + MCP"
- Decision flow pre každú úlohu
- Konkrétne príklady (3) ako sa tieto tri vrstvy reálne spoja
- Hard rules (čeština, žiadne pluginy, alergie nedotknuteľné)

Bez tohto súboru sú Subagenty/Skills/MCP iba pasívnym zoznamom — s ním sa stanú **orchestrovaným nástrojom**.

## Bonus

| Bonus | Kde |
|---|---|
| **Hooks** (PostToolUse logger) | [.claude/settings.json](.claude/settings.json) |
| **Bootstrap skript** (idempotentný setup) | [bootstrap.sh](bootstrap.sh) |
| **Architecture diagram** (mermaid) | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **3 reálne transcripty** ako sa to používa | [examples/](examples/) |

## Odovzdanie

Repo je na GitHub: `<url>`. Submission je adresár [homework/](.).

Doménový kontext (čo je NutriFlow): pozri [README.md](README.md) sekcia „Čo je NutriFlow" alebo živú špec v [../GOAL.md](../GOAL.md).
