---
name: pantry-first-meal-planning
description: Použij když pracuješ na Chef agentovi nebo testuješ pantry-first chování - vynucuje, že Chef preferuje ingredience z PantryContents před nákupem nových. Aktivuj při úpravě chef.md prompt, při debugu "Chef ignoruje pantry", a při psaní testů pro pantry coverage metriku.
---

# pantry-first-meal-planning — Doménový princíp pre Chef

## Kontext

NutriFlow má **`PantryContents`** schému ktorá hovorí, čo má používateľ doma. **Chef agent musí preferovať tieto ingrediencie** pred navrhnutím nákupu. Toto je doménový princíp, ktorý šetrí používateľovi peniaze a redukuje plytvanie.

Tento skill kodifikuje pravidlá ako Chef má rozhodovať a ako sa overuje že to robí správne.

## Kedy invokovať

1. **Píšeš/upravuješ Chef prompt** v `backend/src/nutriflow/prompts/chef.md`.
2. **Debuguješ sťažnosť** typu „Chef navrhol kúpiť ryžu, hoci ju mám doma".
3. **Píšeš test** ktorý meria `pantry_coverage_ratio` (% pantry items skutočne použitých v drafte).
4. **Pracuješ na Critic** rule pre pantry — Critic vie reject-núť draft, ktorý ignoruje pantry.
5. **Refaktoruješ `ShoppingListResult`** — pravidlo je že pantry items sa **nezahŕňajú** do shopping listu.

## Hard Rules

### R1 — Preferencia pantry > čerstvosť > akcie

Chef má 3 signály pri výbere ingrediencie. Priorita:

1. **Pantry (najvyššia)** — ak je v `PantryContents`, použi to.
2. **Čerstvosť** — preferuj sezónne, nie nasilu „bio".
3. **Akcie z Rohlik** (`PromotionContext`) — nice-to-have, ale **nikdy** nevyhráva nad pantry.

```
Pantry vyhráva, akcia je tie-break pri novom nákupe.
```

### R2 — Mark `from_pantry: True` pre každú ingredienciu

V `MealIngredient` schéme:

```python
class MealIngredient(BaseModel):
    name: str
    quantity: float
    unit: str
    from_pantry: bool = False  # ← Chef MUSÍ správne nastaviť
```

**Chef ručne aplikuje pravidlo:** ak `name` (po normalizácii) zhoduje sa s `PantryContents.items[*].name`, nastaví `from_pantry=True`.

Critic to overuje cez `pantry_coverage_check` rule.

### R3 — Shopping list vylučuje pantry items

`ShoppingListResult.items` musí **vylúčiť** všetky `MealIngredient` s `from_pantry=True`. Inak používateľ kupuje, čo už má.

```python
def aggregate_shopping(draft: WeeklyMealDraft) -> list[ShoppingListItem]:
    needed: dict[str, ShoppingListItem] = {}
    for day in draft.days:
        for meal in day.meals:
            for ing in meal.ingredients:
                if ing.from_pantry:
                    continue  # ← skip pantry items
                # ... aggregate ...
    return list(needed.values())
```

### R4 — Quantity validation

Ak používateľ má v pantry „500g ovsenných vločiek" a Chef plánuje použiť 800g cez týždeň → potrebuje zahrnúť **400g do shopping listu** (mínus pantry stock). Toto je advanced — pre MVP postačí: ak `from_pantry=True`, **predpokladáme dostatok**. Pre v2 sa pridá `pantry_quantity` matching.

### R5 — Coverage metrika

`pantry_coverage_ratio = used_pantry_items / total_pantry_items`.

Cieľ: `>= 0.5` (Chef použije aspoň polovicu toho, čo užívateľ má). Pod tým Critic upozorní:
> „Plán využil iba 30% pantry — zvážte revízu."

(Toto je warning, nie error. Plán neblokuje.)

### R6 — Edge case: prázdny pantry

Ak `PantryContents.items == []`:
- `pantry_coverage_ratio = 1.0` (nedáva sa rozdeliť nulou — neutrálne).
- Chef berie iba `PromotionContext` a defaultné suroviny.
- Žiadny warning.

### R7 — Pantry override pri alergii

Ak je v pantry vec, ktorá konfliktuje s `dietary_restrictions` (napr. mlieko, ale používateľ je laktóza-free) → **dietary restrictions vyhrávajú**. Chef tú ingredienciu ignoruje, akoby v pantry nebola. Critic to overí.

## Red flags

| Signál | Akcia |
|---|---|
| Chef draft má `from_pantry=False` pre ingredienciu ktorá je v `PantryContents` | Reject. Buď Chef prompt nedostáva pantry alebo ignoruje. Skontroluj `chef.md`. |
| `ShoppingListResult` obsahuje ingredienciu s `from_pantry=True` z draftu | Reject. Aggregation logic je broken — neoodfiltrovala pantry items. |
| `pantry_coverage_ratio < 0.3` opakovane | Investigate. Pravdepodobne Chef prompt nemá explicitnú pantry-first inštrukciu, alebo few-shot examples ju nedemonštrujú. |
| Chef ignoruje pantry „lebo akcia z Rohliku je lacnejšia" | Reject. R1 je explicitné: pantry > akcia. |
| Test pre pantry coverage nemá fixture s realistickým pantry (3-10 items) | Reject. Test s prázdnym pantry netestuje nič. |

## Príklad — Chef prompt fragment

### ✅ Správny prompt

```markdown
Si Chef agent NutriFlow. Plánuješ 7-dňové menu pre českého používateľa.

## Pantry-first pravidlo

Používateľ ti dáva `PantryContents` so zoznamom toho, čo má **už doma**. Tvoje pravidlo:

1. **PREFERUJ** ingrediencie z pantry pred novými nákupmi.
2. Pre každú ingredienciu v `MealIngredient` nastav `from_pantry: true` ak je v `PantryContents`, inak `false`.
3. Cieľ: použiť aspoň **polovicu** pantry items niekde v týždennom pláne.

## Príklad

Vstup `PantryContents.items`:
- ovsené vločky (500g)
- arašidové maslo (250g)
- vajcia (10 ks)

Tvoj raňajkový recept by mal:
- IDEÁLNE: ovsené vločky + vajcia + arašidové maslo (cover 3/3)
- OK: ovsené vločky + vajcia (cover 2/3)
- NEDOBRÉ: müsli + jogurt (cover 0/3, ignoruje pantry)

## Validation

Critic ťa odmietne ak:
- `pantry_coverage_ratio < 0.5` (warning, nie reject)
- `from_pantry` flag je nesprávny vo viac ako 10% ingredients
```

### ❌ Zlý prompt

```markdown
Si Chef. Naplánuj 7 dní jedál. Daj výstup v JSON.
```

(Žiadne pantry pravidlá → Chef bude ignorovať `PantryContents`.)

## Cross-references

- České výstupy: [`czech-llm-output`](../czech-llm-output/SKILL.md)
- Typed handoff: [`agent-handoff-contracts`](../agent-handoff-contracts/SKILL.md)
- Routing: [`../../../CLAUDE.md`](../../../CLAUDE.md) tabuľka, riadok pre `prompt-engineer-cs` a `agent-sdk-builder`
- Chef prompt: `backend/src/nutriflow/prompts/chef.md`
- Critic rules: `GOAL.md §14`
- Shopping list aggregation: `backend/src/nutriflow/agents/shopper.py`

## Definition of Done pre úlohu kde tento skill bežal

- [ ] Chef prompt obsahuje explicitné pantry-first pravidlo s príkladom
- [ ] `MealIngredient.from_pantry` je správne nastavený pre každú ingredienciu
- [ ] `ShoppingListResult.items` neobsahuje items s `from_pantry=True`
- [ ] Test pre `pantry_coverage_ratio >= 0.5` prejde na fixture s 5+ pantry items
- [ ] Critic warning sa triggeruje pri `pantry_coverage_ratio < 0.5`
- [ ] Žiadny konflikt medzi pantry a dietary_restrictions (R7)
