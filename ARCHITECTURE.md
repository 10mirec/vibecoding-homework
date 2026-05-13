# ARCHITECTURE.md — Ako sa Subagenty + Skills + MCP servery spájajú

## Vysokoúrovňový diagram

```mermaid
flowchart TB
    User([Používateľ])
    Claude[Hlavný Claude<br/>v Claude Code]
    CLAUDE_MD[CLAUDE.md<br/>routing tabuľka]

    subgraph subagents [".claude/agents/ — 8 Subagentov"]
        SA1[backend-architect]
        SA2[db-modeler]
        SA3[schema-designer]
        SA4[agent-sdk-builder]
        SA5[prompt-engineer-cs]
        SA6[mcp-integrator]
        SA7[frontend-builder]
        SA8[test-writer]
    end

    subgraph skills [".claude/skills/ — 3 Skills"]
        SK1[czech-llm-output]
        SK2[agent-handoff-contracts]
        SK3[pantry-first-meal-planning]
    end

    subgraph mcp [".mcp.json — 3 MCP Servery"]
        MCP1[postgres<br/>npm]
        MCP2[filesystem<br/>npm]
        MCP3[rohlik-promo<br/>custom Python]
    end

    User -->|prompt| Claude
    Claude -->|čítá pravidlá| CLAUDE_MD
    CLAUDE_MD -.routing.-> Claude
    Claude -->|dispatch| subagents
    Claude -->|aktivuje| skills
    Claude -->|volá tool| mcp

    subagents -.referencujú.-> skills
    subagents -.volajú.-> mcp
```

## Mapping tabuľka — kto koho používa

| Subagent | Skills, ktoré používa | MCP servery, ktoré používa |
|---|---|---|
| **backend-architect** | `agent-handoff-contracts` | `filesystem` |
| **db-modeler** | `agent-handoff-contracts` | `postgres` |
| **schema-designer** | `agent-handoff-contracts` | `filesystem`, `postgres` |
| **agent-sdk-builder** | `agent-handoff-contracts`, `pantry-first-meal-planning`, `czech-llm-output` | `rohlik-promo`, `postgres` |
| **prompt-engineer-cs** | `czech-llm-output`, `pantry-first-meal-planning` | — |
| **mcp-integrator** | — | `rohlik-promo` |
| **frontend-builder** | `czech-llm-output` (UI texty) | `filesystem` |
| **test-writer** | `agent-handoff-contracts` | `postgres`, `rohlik-promo` |

**Pozorovanie:** Nie každý subagent používa všetky vrstvy. `mcp-integrator` napríklad nemá relevantný skill (jeho doména je iba MCP plumbing). `prompt-engineer-cs` zase nemá MCP server (jeho doména je čistý text). To je **správne** — ak by sme každému dali všetko, stratíme signál.

## Prečo táto trojica spolu

Tieto tri primitivy Claude Code sa **doplňujú**:

| Primitive | Sila | Slabina | Kompenzuje |
|---|---|---|---|
| **Subagent** | Špecializované kontext-okno, nezahltí hlavnú konverzáciu | Štatické — má pevný prompt, nereaguje na aktuálne dáta | MCP dodá runtime dáta |
| **Skill** | Aktivuje sa *na podnet*, vynúti pravidlo v správny moment | Nevykonáva — len inštruuje | Subagent vykoná, MCP dodá info |
| **MCP server** | Externý zdroj live dát (DB, filesystem, custom toolu) | Bez kontextu na ich použitie — len API | Subagent vie kedy ich použiť, Skill povie ako |

**Bez všetkých troch:** ak by sme mali iba Subagentov, hlavný Claude by hovoril *„rob X"* ale nevynútil by žiadnu konvenciu. Iba Skills bez Subagentov: Claude by sa vyčerpal pri kontextu pre veľké úlohy. Iba MCP: Claude má dáta ale nevie ako ich použiť konzistentne.

## Decision flow — kedy ktorý použiť

Pri každej úlohe sa pýtaj v tomto poradí:

```
Q1: Je úloha veľká / mimo aktuálneho kontextu hlavnej konverzácie?
    → ÁNO: dispatch Subagent (nezahltí hlavné context window)
    → NIE: pokračuj sám

Q2: Existuje pravidlo / konvencia, ktorá sa pri tomto type úlohy musí dodržať?
    → ÁNO: aktivuj Skill PRED akciou (vynúti pravidlo)
    → NIE: pokračuj

Q3: Potrebuješ runtime dáta (DB stav, filesystem, externý API)?
    → ÁNO: zavolaj MCP tool
    → NIE: hotovo, vykonaj
```

## Konkrétny príklad orchestrácie

**Scenár:** Užívateľ povie *„Pridaj endpoint POST /feedback pre uloženie hodnotenia jedla."*

```mermaid
sequenceDiagram
    participant U as Užívateľ
    participant C as Hlavný Claude
    participant SK_AHC as skill:<br/>agent-handoff-contracts
    participant SA_SD as subagent:<br/>schema-designer
    participant SA_DM as subagent:<br/>db-modeler
    participant MCP_PG as MCP:<br/>postgres
    participant SA_BA as subagent:<br/>backend-architect
    participant SA_TW as subagent:<br/>test-writer

    U->>C: "Pridaj POST /feedback"
    C->>C: čítam CLAUDE.md routing
    C->>SK_AHC: aktivujem (Pydantic v2 rules)
    C->>SA_SD: dispatch — vytvor FeedbackPayload
    SA_SD-->>C: schema hotová
    C->>SA_DM: dispatch — overiť DB tabuľku
    SA_DM->>MCP_PG: query introspekcia meal_feedback
    MCP_PG-->>SA_DM: aktuálne stĺpce
    SA_DM-->>C: migrácia nepotrebná / hotová
    C->>SA_BA: dispatch — pridaj endpoint
    SA_BA-->>C: endpoint hotový
    C->>SA_TW: dispatch — integration test
    SA_TW->>MCP_PG: test DB state
    SA_TW-->>C: testy zelené
    C->>U: hotovo, prosím review
```

## Súbory na hlbšie štúdium

- [CLAUDE.md](CLAUDE.md) — routing tabuľka + decision flow
- [.claude/agents/](.claude/agents/) — 8 subagent definícií
- [.claude/skills/](.claude/skills/) — 3 SKILL.md
- [.mcp.json](.mcp.json) — MCP server registrácia
- [mcp_servers/rohlik_promo/server.py](mcp_servers/rohlik_promo/server.py) — implementácia custom MCP servera
- [examples/](examples/) — 3 reálne transcripty
