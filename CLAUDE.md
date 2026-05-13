# CLAUDE.md — NutriFlow agent workspace

> **Pro Claude Code.** Tento soubor je *prvý*, ktorý Claude Code načítá pri otvorení tohto adresára ako workspace. Definuje **kedy a v akom poradí** invokovať Subagentov, Skills a MCP servery. Bez tohto súboru sú tieto tri vrstvy len pasívnym zoznamom — s ním sa stávajú orchestrovaným nástrojom.

## Čo je tento workspace

Samostatne stojaca konfigurácia pre prácu na **NutriFlow** — osobnom MVP pre týždenné plánovanie jedál v češtine, postavenom na multi-agent orchestrácii cez Claude Agent SDK (5 runtime agentov: Orchestrator + Nutritionist + Chef + Shopper + Critic).

Tento workspace ukazuje tri základné Claude Code primitivy:

| Vrstva | Čo to je | Kde sa nachádza |
|---|---|---|
| **Subagenty** | Špecializovaní implementační agenti dispatchovaní hlavným Claudeom | [.claude/agents/](.claude/agents/) — 8 ks |
| **Skills** | Vynucované pravidlá/pracovné postupy pre konkrétne situácie | [.claude/skills/](.claude/skills/) — 3 ks |
| **MCP Servery** | Externé tool-providery komunikujúce stdio protocolom | [.mcp.json](.mcp.json) + [mcp_servers/](mcp_servers/) — 3 ks |

## Pravidlá projektu (z live `CLAUDE.md` v root NutriFlow)

Tieto pravidlá sú **nenegociovateľné** a aplikujú sa pri každej úlohe:

1. **Čeština všade** — UI texty, error messages, LLM prompty aj LLM výstupy. Žiadne anglické texty smerom k používateľovi.
2. **Typed handoff iba** — agenti si predávajú dáta výhradne cez Pydantic v2 schémy z `backend/src/nutriflow/domain/schemas.py`. Žiaden voľný text medzi agentmi.
3. **Alergie nedotknuteľné** — žiaden agent ani fallback nesmie navrhnúť jedlo porušujúce dietary restrictions. Pri konflikte plán fail-uje, nie kompromis.
4. **Shopper failure ≠ workflow failure** — ak Rohlik MCP zlyhá, plán sa dokončí so shopping listom bez cart syncu.
5. **Žiadne pluginy / marketplace** — všetky Skills sú **lokálne súbory** v `.claude/skills/`, žiaden `enabledPlugins`.
6. **TDD je default** — pre každý nový kus produkčného kódu (model, endpoint, agent, service) najprv test, potom implementácia.

## ★ Routing tabuľka — kedy čo invokovať

Toto je **srdce CLAUDE.md**. Keď príde úloha, identifikuj v tabuľke najpodobnejší riadok a sleduj jeho stĺpce.

| Užívateľ chce... | Použi subagenta | Aktivuj skill | Volaj MCP server |
|---|---|---|---|
| Pridať/zmeniť **Pydantic schému** (domain contract) | `schema-designer` | `agent-handoff-contracts` | `filesystem` (čítanie existujúcich), `postgres` (overiť či nemá byť aj DB stĺpec) |
| Pridať/zmeniť **DB tabuľku** alebo migráciu | `db-modeler` | `agent-handoff-contracts` (ak sa dotýka schém) | `postgres` (živá introspekcia schémy + DDL preview) |
| Implementovať/upraviť **runtime LLM agenta** (Orchestrator, Nutritionist, Chef, Shopper, Critic) | `agent-sdk-builder` | `agent-handoff-contracts` + `pantry-first-meal-planning` (pre Chef) | `rohlik-promo` (Shopper integration testy) |
| Napísať/vyladiť **český LLM prompt** | `prompt-engineer-cs` | `czech-llm-output` | — |
| **Chef halucinuje** alebo nedrží sa pantry-first | `prompt-engineer-cs` | `czech-llm-output` + `pantry-first-meal-planning` | — |
| **Rohlik MCP integrácia** (adapter v `backend/src/nutriflow/tools/`) | `mcp-integrator` | — | `rohlik-promo` (real-time test mock failures) |
| Postaviť **FastAPI endpoint / app factory** | `backend-architect` | `agent-handoff-contracts` (ak má request/response schemu) | — |
| Postaviť **Next.js stránku / shadcn komponent** | `frontend-builder` | `czech-llm-output` (pre Czech UI texty) | `filesystem` (číta backend schémy pre zod mirror) |
| Napísať **testy** (unit/integration/e2e) | `test-writer` | `agent-handoff-contracts` (test contract drift) | `postgres` (test DB state), `rohlik-promo` (mock failures) |

### Decision flow pre každú úlohu

```
1. ČO je úloha?
   → Mapuj na riadok v routing tabuľke.

2. PRED kódom: aktivuj relevantný Skill.
   → Skill vynúti pravidlá. Bez skill-u môžeš porušiť konvenciu, ktorú si nezapamätal.

3. AK potrebuješ runtime info (DB stav, MCP odpoveď):
   → Zavolaj MCP tool z .mcp.json. Nečakaj že "spomenieš si" — pýtaj sa nástroja.

4. AK je úloha väčšia ako trivialny edit:
   → Dispatch-ni subagenta podľa tabuľky. Hlavný Claude sa nepúšťa do implementácie sám.

5. PO kóde: verification (testy, lint, smoke run).
   → Žiadne "malo by to fungovať". Spusti.
```

## Príklady aplikovania routing

**Príklad 1 — „Pridaj endpoint POST /feedback":**

1. Toto je **API endpoint + nová Pydantic schema + možná DB tabuľka**.
2. Krok 1: dispatch `schema-designer` → pred prácou aktivuje skill `agent-handoff-contracts`. Vytvorí `FeedbackPayload` v `domain/schemas.py`.
3. Krok 2: dispatch `db-modeler` → použije MCP tool `postgres` na overenie že tabuľka `meal_feedback` ešte nemá tieto stĺpce. Vytvorí migráciu.
4. Krok 3: dispatch `backend-architect` → pridá endpoint, request/response typed cez schému z kroku 1.
5. Krok 4: dispatch `test-writer` → integration test proti reálnej Postgres (`postgres` MCP server pre setup).

**Príklad 2 — „Chef negeneruje pantry-first jedlá":**

1. Toto je **kvalita LLM výstupu**.
2. Krok 1: aktivuj skill `pantry-first-meal-planning` → vysvetlí čo Chef môže porušovať.
3. Krok 2: aktivuj skill `czech-llm-output` → kontroluje gramatiku/terminologiu output.
4. Krok 3: dispatch `prompt-engineer-cs` → opraví `backend/src/nutriflow/prompts/chef.md`.
5. Krok 4: dispatch `test-writer` → regression test že Chef preferuje pantry items.

**Príklad 3 — „Rohlik MCP padá pri sync_cart":**

1. Toto je **MCP integration bug**.
2. Krok 1: zavolaj MCP tool `rohlik-promo.get_status()` → over si že server beží.
3. Krok 2: dispatch `mcp-integrator` → opraví adapter v `backend/src/nutriflow/tools/rohlik_mcp.py`.
4. Krok 3: dispatch `test-writer` → regression test pre `MCPUnavailable` fallback.

## Verifikačná rutina

Pred označením úlohy za hotovú spusti:

```bash
# Backend
cd backend && uv run pytest && uv run ruff check . && uv run mypy src

# Frontend (ak sa dotklo UI)
cd frontend && pnpm build && pnpm typecheck && pnpm lint

# MCP server (ak sa dotklo)
cd homework/mcp_servers/rohlik_promo && uv run python -c "from server import mcp; print('OK')"
```

**Žiadne TODOs, žiadne `xfail` bez issue trackingu, žiadne `# type: ignore` bez komentára prečo.**

## Out of scope — čo nerobiť

- Žiadne ďalšie jazyky než čeština (ani toggle, ani i18n infraštruktúru).
- Žiadna autentifikácia nad rámec dev session tokenu.
- Žiadne pluginy/marketplace.
- Žiadne mock DB v integration testoch — reálna Postgres v dockeri.
- Žiadne `--no-verify` pri commitoch.

## Referenčné súbory

- [README.md](README.md) — úvod, ako otvoriť tento workspace
- [ARCHITECTURE.md](ARCHITECTURE.md) — diagram + mapping tabuľky
- [../GOAL.md](../GOAL.md) — autoritatívna špecifikácia NutriFlow projektu
- [../CLAUDE.md](../CLAUDE.md) — pravidlá live projektu (rozšírená verzia tohto súboru)
