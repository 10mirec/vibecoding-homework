---
name: agent-handoff-contracts
description: Použij když navrhuješ nebo měníš Pydantic v2 schéma pro handoff mezi NutriFlow agenty (Orchestrator/Nutritionist/Chef/Shopper/Critic) - vynucuje typed-only handoff, žádný volný text mezi agenty, schéma jako single source of truth pro API i agent payload. Aktivuj před každou změnou backend/src/nutriflow/domain/schemas.py.
---

# agent-handoff-contracts — Typed handoff medzi agentmi

## Kedy invokovať

Tento skill **MUSÍŠ** aktivovať, keď:

1. **Pridávaš/meníš schému** v `backend/src/nutriflow/domain/schemas.py`.
2. **Meníš I/O signature** `BaseAgent` alebo konkrétneho agenta (`Nutritionist`, `Chef`, `Shopper`, `Critic`).
3. **Pridávaš endpoint** ktorý zdieľa schému s agentom (typický pattern: request body = agent input).
4. **Píšeš test pre contract drift** medzi backend a frontend zod (frontend zod musí byť 1:1 mirror).
5. **Refaktoruješ tool/handler** ktorý vracia data spotrebovávané agentom.

## Hard Rules

### R1 — Pydantic v2 only

- `from pydantic import BaseModel, Field, ConfigDict` — žiadne v1 imports.
- `model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)` — extra polia ako error.
- `Field(...)` pre required, `Field(default=...)` pre optional s defaultom, `Field(default=None)` pre nullable.
- Pre union typov používaj `X | Y` (PEP 604), nie `Union[X, Y]`.

### R2 — Single source of truth

Schéma v `backend/src/nutriflow/domain/schemas.py` slúži pre **3 účely zároveň**:

1. **API request/response** (FastAPI deps cez `Annotated[Schema, Body(...)]`)
2. **Agent input/output** (`BaseAgent[Input, Output]` generics)
3. **DB serialization snapshot** (ukladá sa do `agent_runs.input_json` / `output_json`)

Preto:
- **Žiadne API-only fieldy** ako `pagination_token` v doménovej schéme. Ak je potrebné, vytvor wrapper `MyApiResponse` zvonku.
- **Žiadne ORM relationships** v doménovej schéme. ORM žije v `db/models/`.
- **Žiadne LLM raw response** v schéme. LLM výstup je parsovaný do schémy, nie naopak.

### R3 — Žiaden voľný text medzi agentmi

Agenti si **nesmú** posielať plain string ako handoff payload. Aj keď je to len jedna veta. Vždy:

```python
# ❌ ZLE
def critic_to_chef_handoff(reason: str) -> None: ...

# ✅ SPRÁVNE
class ValidationResult(BaseModel):
    passed: bool
    issues: list[ValidationIssue]
    revision_prompt_cs: str | None = None

def critic_to_chef_handoff(result: ValidationResult) -> None: ...
```

**Prečo:** voľný text = parsovanie regexem = krehkosť. Typed = mypy chyta zmeny + serializácia do `agent_runs` JSON snapshot.

### R4 — Nullable explicitne

- Nepoužívaj `Optional[X]` — používaj `X | None`.
- Vždy explicitný default: `Field(default=None)`.
- V JSON sa to seriálizuje ako `null`. Nikdy nevyhadzuj nullable field z payloadu „lebo ušetríme bytes".

### R5 — Numeric coercion vypnutá

```python
class DailyTargets(BaseModel):
    model_config = ConfigDict(extra="forbid", coerce_numbers_to_str=False)
    calories: int = Field(..., gt=0)
    protein_g: float = Field(..., ge=0)
```

LLM môže vrátiť `"380"` namiesto `380` — chceme to zachytiť ako error, nie ticho coerce-nuť.

### R6 — JSON round-trip MUSÍ fungovať

Každá schéma musí prejsť testom:

```python
def test_round_trip():
    original = MySchema(field=...)
    json_str = original.model_dump_json()
    restored = MySchema.model_validate_json(json_str)
    assert restored == original
```

**Prečo:** `agent_runs.input_json` ukladá schémy ako JSONB v Postgres. Pri rerun-e plánu sa schéma deserializuje. Round-trip drift = strata dát.

### R7 — Schéma evolution backwards-compatible

Pri pridávaní nového poľa **vždy** s defaultom:

```python
# Pôvodne
class Meal(BaseModel):
    name: str
    calories: int

# Pridanie nového poľa — backwards compatible
class Meal(BaseModel):
    name: str
    calories: int
    preparation_time_min: int = Field(default=15)  # ← default!
```

Pri odoberaní starého poľa **najprv deprecate** (1 release cycle), potom remove. Pre MVP NutriFlow tento cyklus nie je formálny, ale princíp drží: nedotýkaj sa polí ktoré sú v live `agent_runs` JSONB snapshotoch.

### R8 — Frontend zod zrkadlo

Frontend (`frontend/src/lib/schemas.ts`) má **zod schémy s presne tými istými** field names ako Pydantic. Pri zmene:

1. Najprv backend Pydantic.
2. Hneď potom frontend zod.
3. Test driftu (Playwright e2e alebo type-level test).

## Red flags

| Signál | Akcia |
|---|---|
| Schéma má `Any` alebo `dict[str, Any]` | Reject. Daj explicitné polia. Ak naozaj treba blob → `Json[dict[str, MySubSchema]]`. |
| Schéma duplikuje ORM model (pole-za-poľom) | Reject. Pridaj converter v service vrstve, nie cez dvojitú definíciu. |
| Schéma má method s biznes logikou | Move logiku do service vrstvy. Schéma = data, nie behavior. |
| Schéma má `Config: orm_mode = True` (v1) | Reject. Pydantic v2 už nemá `orm_mode`. |
| Nullable bez explicitného `\| None` | Reject. Mypy strict to chytí ako error. |
| Schéma fields v PascalCase | Reject. Vždy `snake_case`. |
| API endpoint má wrapper schému zámiešanú s doménovou | Move wrapper do `api/v1/schemas.py` (API-only), doménová zostane čistá. |

## Príklad — Critic ValidationResult

### ✅ Správna definícia

```python
# backend/src/nutriflow/domain/schemas.py
from pydantic import BaseModel, ConfigDict, Field

class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    severity: Literal["error", "warning"]
    rule_id: str = Field(..., min_length=1)
    message_cs: str
    affected_days: list[int] = Field(default_factory=list)


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    passed: bool
    issues: list[ValidationIssue]
    revision_prompt_cs: str | None = None
```

### ✅ Použitie v agentovi

```python
# backend/src/nutriflow/agents/critic.py
class Critic(BaseAgent[CriticInput, ValidationResult]):
    async def run(self, input: CriticInput) -> ValidationResult:
        # ...llm volanie...
        raw_json = await self._llm.complete(prompt, response_schema=ValidationResult)
        return ValidationResult.model_validate_json(raw_json)
```

### ❌ Anti-pattern

```python
# Critic vracia string s issues — netyped, neserializuje sa do agent_runs správne
async def run(self, input: dict) -> str:
    return "passed: true; issues: 0"  # ← REJECT
```

## Cross-references

- České výstupy: [`czech-llm-output`](../czech-llm-output/SKILL.md)
- Pantry princíp: [`pantry-first-meal-planning`](../pantry-first-meal-planning/SKILL.md)
- Routing: [`../../../CLAUDE.md`](../../../CLAUDE.md) tabuľka, riadky pre `schema-designer`, `db-modeler`, `agent-sdk-builder`
- Pydantic v2 docs: `https://docs.pydantic.dev/2.0/`

## Definition of Done pre úlohu kde tento skill bežal

- [ ] Schéma v `backend/src/nutriflow/domain/schemas.py` má `ConfigDict(extra="forbid")`
- [ ] Žiadne `Any` ani `dict[str, Any]` (pokiaľ vyložene nejde o blob s nested schémou)
- [ ] Mypy strict prejde (`uv run mypy src/nutriflow/domain/`)
- [ ] Round-trip JSON test prejde
- [ ] Frontend zod schéma (ak existuje) je zarovnaná field-by-field
- [ ] `agent_runs` JSONB snapshot stále parsovateľný (žiadny destrukčný rename)
