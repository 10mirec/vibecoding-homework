# NutriFlow — Nastavenie kódovacího Agenta

Konfigurácia kódovacieho agenta postavená na **MCP Serveroch, Skills a Subagentoch** (bez pluginov a marketplace).

**Platforma:** Claude Code
**Projekt:** [NutriFlow](../GOAL.md) — osobné MVP pre týždenné plánovanie jedál (multi-agent orchestrácia, Czech-only)

---

## Čo je v tomto adresári

Kompletná Claude Code konfigurácia ukazujúca 3 primárne primitivy:

- **8 Subagentov** v [.claude/agents/](.claude/agents/) — špecializovaní implementační agenti
- **3 lokálne Skills** v [.claude/skills/](.claude/skills/) — vynucované pracovné postupy
- **3 MCP servery** v [.mcp.json](.mcp.json) — externé tool-providery (2 verejné + 1 vlastný v Pythone)

**Žiadne pluginy, žiadny marketplace.** Všetko je v repe ako súbory.

Tieto tri vrstvy drží pohromade **[CLAUDE.md](CLAUDE.md)** — orchestrátor, ktorý definuje *kedy a v akom poradí* invokovať čo.

## Prehľad konfigurácie

| Vrstva | Súbor / adresár | Počet |
|---|---|---|
| MCP Servery | [.mcp.json](.mcp.json), [mcp_servers/rohlik_promo/](mcp_servers/rohlik_promo/) | 3 |
| Skills | [.claude/skills/](.claude/skills/) | 3 |
| Subagenty | [.claude/agents/](.claude/agents/) | 8 |
| Žiadne plugins | [.claude/settings.json](.claude/settings.json) — bez `enabledPlugins` | ✓ |
| Orchestrátor (lepidlo medzi nimi) | [CLAUDE.md](CLAUDE.md) | 1 |

## Rychlý start

```bash
# 1. Klonuj NutriFlow repo
git clone https://github.com/<user>/NutriFlow.git
cd NutriFlow/homework

# 2. Spusti bootstrap (overí dependencies + nainštaluje custom MCP server)
bash bootstrap.sh

# 3. Otvor tento adresár v Claude Code ako workspace
#    Claude automaticky načítá CLAUDE.md a uvidí všetkých 8 subagentov,
#    3 skills a 3 MCP servery.

# 4. Skús prompt napríklad:
#    "Pridaj novú Pydantic schému FeedbackPayload"
#    → Claude podľa routing tabuľky v CLAUDE.md dispatch-ne
#      subagent `schema-designer`, aktivuje skill `agent-handoff-contracts`
#      a možno použije MCP tool `postgres` pre introspekciu DB.
```

## Štruktúra

```
.
├── README.md              ← si tu
├── CLAUDE.md              ← ★ orchestrátor, prvé čo Claude Code načíta
├── ARCHITECTURE.md        ← diagram + mapping tabuľky 8×3×3
├── bootstrap.sh           ← idempotentný setup skript
├── .claude/
│   ├── settings.json      ← pluginless config + hook bonus
│   ├── agents/            ← 8 subagentov (každý s "Skills a MCP" sekciou)
│   └── skills/            ← 3 SKILL.md (czech-llm-output, agent-handoff-contracts, pantry-first-meal-planning)
├── .mcp.json              ← postgres + filesystem + rohlik-promo
├── mcp_servers/
│   └── rohlik_promo/      ← custom Python MCP server (FastMCP, stdio)
└── examples/              ← 3 transcripty (subagent dispatch, skill invocation, MCP tool call)
```

## Čo je NutriFlow

Osobné MVP pre **jedného českého používateľa** ktoré generuje **týždenné plány jedál** + **nákupné zoznamy** s napojením na **Rohlik** (česká e-grocery sieť).

Hlavná hodnota: **reálna orchestrácia 5 LLM agentov** cez Claude Agent SDK:

- **Orchestrator** — riadi workflow (happy path / revise loop / fallback)
- **Nutritionist** — vypočíta `DailyTargets` (kalórie + makrá), prevažne deterministicky
- **Chef** — generuje `WeeklyMealDraft` (7 dní × N jedál) v češtine, pantry-first
- **Shopper** — recon (akcie z Rohliku) + finalize (vytvorí košík)
- **Critic** — validuje draft proti pravidlám, vracia `passed: bool` + issues

Subagenty v `.claude/agents/` slúžia ako **implementační** pomocníci — sú to coding agenti, nie runtime agenti. (Runtime agenti žijú v `backend/src/nutriflow/agents/`.)

Hlbší kontext: [GOAL.md](../GOAL.md), [CLAUDE.md (live)](../CLAUDE.md), [PLAN.md](../PLAN.md).

## Ako sa to celé spojí

Pozri [ARCHITECTURE.md](ARCHITECTURE.md) pre diagram a detailný mapping. Krátko:

```
                    ┌─────────────────────┐
                    │   Hlavný Claude     │
                    │   (čítá CLAUDE.md)  │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
         ┌────────────┐ ┌────────────┐ ┌────────────┐
         │ 8 Subagent │ │  3 Skill   │ │ 3 MCP svr  │
         │  (dispat-  │ │ (vynútiť   │ │ (externé   │
         │   chuj)    │ │  pravidlo) │ │  tooly)    │
         └────────────┘ └────────────┘ └────────────┘
```

CLAUDE.md má **routing tabuľku** ktorá pre každý typ úlohy povie: *„dispatch subagent X, aktivuj skill Y, použi MCP server Z"*. To je „lepidlo" — bez nej sú tieto tri vrstvy len pasívnym zoznamom.

