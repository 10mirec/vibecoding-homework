# Príklad 01 — Subagent Dispatch

> Ako Claude Code rozpozná, že úloha patrí špecializovanému subagentovi, a dispatchne ho s presnými inštrukciami.

## Scenár

Užívateľ pracuje na NutriFlow a chce pridať nové DB pole.

## Konverzácia

### 👤 Užívateľ

> Pridaj pole `notes` do tabuľky `meal_feedback` — má byť `text NULL`. Treba migráciu aj update na ORM model.

### 🤖 Claude (hlavná konverzácia)

> Pozriem CLAUDE.md routing tabuľku.

Z `CLAUDE.md` riadok:

| Užívateľ chce... | Subagent | Skill | MCP |
|---|---|---|---|
| Pridať/zmeniť DB tabuľku alebo migráciu | `db-modeler` | `agent-handoff-contracts` | `postgres` |

> Toto je doménová úloha pre `db-modeler` subagenta. Najprv aktivujem skill `agent-handoff-contracts` pre prípad že nová schéma sa dotkne aj Pydantic, a dispatch-nem.

```
[Skill] agent-handoff-contracts aktivovaný — pripomenutie:
  - Pydantic v2 only
  - nullable explicitne (X | None)
  - žiadne Any
```

> Zavolám MCP tool postgres pre overenie aktuálnej schémy:

```
mcp__postgres__query("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='meal_feedback'")

→ [{"column_name": "id", "data_type": "uuid"},
   {"column_name": "meal_id", "data_type": "uuid"},
   {"column_name": "rating", "data_type": "integer"},
   {"column_name": "created_at", "data_type": "timestamp"}]
```

> Pole `notes` neexistuje. Teraz dispatch `db-modeler` s celým kontextom:

```
[Agent dispatch] db-modeler:
  Task: "Pridaj pole notes text NULL do meal_feedback tabuľky.
         Aktuálne stĺpce: id, meal_id, rating, created_at (zistené z postgres MCP).
         1) Update ORM model v backend/src/nutriflow/db/models/meal_feedback.py
         2) Vytvor Alembic revision
         3) Spusti uv run alembic check (autogenerate diff má byť prázdny)
         Skill agent-handoff-contracts: ak pole pridáš aj do Pydantic schémy
         FeedbackPayload v domain/schemas.py, použi `notes: str | None = None`."
```

### 🔧 Subagent `db-modeler` (samostatný kontext)

Subagent vidí dispatch task. Pracuje **vo svojom vlastnom context window** (nezahltí hlavný).

```
[db-modeler reading backend/src/nutriflow/db/models/meal_feedback.py]
[db-modeler editing model: pridáva notes: Mapped[str | None] = mapped_column(Text, nullable=True)]
[db-modeler running: uv run alembic revision --autogenerate -m "Add notes to meal_feedback"]
[db-modeler running: uv run alembic check]
✓ done. Created revision abc123.
```

### 🤖 Claude (späť v hlavnej konverzácii)

> `db-modeler` hotový. Migrácia `abc123` pridáva `notes TEXT NULL`. ORM model aktualizovaný. `alembic check` prešiel — žiadny driff.

> Potrebuješ aj endpoint pre POST tohto poľa? Ak áno, dispatch-nem `backend-architect` + `schema-designer`.

---

## Čo ukazuje tento príklad

1. **Routing tabuľka funguje** — CLAUDE.md jasne smerovala úlohu na `db-modeler`, nie iba podľa „cítenia".
2. **Skill aktivovaný PRED dispatchom** — `agent-handoff-contracts` pripomenul pravidlá pre prípad, že subagent vytvorí aj Pydantic.
3. **MCP tool dodal runtime info** — `postgres` introspekcia povedala, že pole skutočne neexistuje (nie „pravdepodobne neexistuje").
4. **Subagent dostal kontext-rich task** — nielen „pridaj notes", ale aj aktuálny stav DB a ktorý skill rešpektovať.
5. **Hlavná konverzácia ostala čistá** — subagent pracoval vo vlastnom okne, hlavný Claude dostal iba zhrnutie.

## Súbory dotknuté

- `backend/src/nutriflow/db/models/meal_feedback.py` (ORM model update)
- `backend/alembic/versions/abc123_add_notes_to_meal_feedback.py` (nová migrácia)
