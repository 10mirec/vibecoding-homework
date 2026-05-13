---
name: czech-llm-output
description: Použij když píšeš nebo validuješ český LLM výstup pro NutriFlow agenty - kontroluje terminologii, gramatiku, JSON schema compliance, alergeny a typed handoff. Aktivuj před každou úpravou prompts/*.md, před regenerací LLM výstupu, nebo když Critic odmítl Chef draft kvůli textovým problémům.
---

# czech-llm-output — Pravidlá pre české LLM výstupy v NutriFlow

## Kedy invokovať

Tento skill **MUSÍŠ** aktivovať, keď:

1. **Píšeš alebo upravuješ prompt** v `backend/src/nutriflow/prompts/*.md` (Nutritionist, Chef, Shopper, Critic).
2. **Validuješ LLM výstup** — či je v plynnej češtine, drží sa terminológie, JSON parse-able.
3. **Critic odmietol draft** s `revision_prompt_cs` — pred tým, než pošleš Chef-ovi revision, prejdi tento skill.
4. **Refaktoruješ Pydantic schému** ktorá obsahuje pole končiace `_cs` (napríklad `reason_cs`, `description_cs`, `revision_prompt_cs`).

## Hard Rules (nenegociovateľné)

Tieto pravidlá majú **prioritu pred elegantnosťou** alebo „prirodzene znejúcim" anglicizmom.

### R1 — Čeština všade

- Žiadne anglické termíny v užívateľsky-viditeľnom texte. Žiadne „protein shake", „meal prep", „workout". Použiť: **bielkovinový kokteil**, **príprava jedál vopred**, **tréning**.
- Žiadne anglické JSON field names v `_cs` poliach. (Field name môže byť `reason_cs`, ale jeho **hodnota** je vždy plynná čeština.)
- Iba ak je technický termín *prijatý v českej kuchynskej praxi* (napríklad „smoothie", „pizza"), môže ostať.

### R2 — Kuchynská terminológia

Konkrétne terminologické voľby, ktoré drží Chef:

| ❌ Nepoužívaj | ✅ Použi |
|---|---|
| „dezert" (anglicizmus zvyšne, akceptovateľné, ale preferuj…) | „zákusek", „moučník" |
| „lunch" / „obiad" (slovensky) | „oběd" |
| „smajdy", „šnek" | správny slovenský/český názov: „šnečí pečivo", „strúhanka" |
| „proteínový" | „bielkovinový" (pokiaľ je to v primárnom texte) |
| „burger" — keď je to české jedlo | „karbanátok", „placička" |
| časti tela hovorovo (napr. „brácha") | spisovne (cieľová skupina = dospelý používateľ aplikácie) |

**Mäso, ryby a strukoviny:** vždy spisovne (kuracie, hovädzie, treska, červené šošovice — nie „šošovku" alebo „losos" bez prepnutia jazyka).

### R3 — Alergie sú nedotknuteľné

Ak `UserProfile.dietary_restrictions` obsahuje alergén, Chef **nikdy** nesmie navrhnúť:
- jedlo s tou ingredienciou,
- jedlo „bez X, ale postavené na X" (napríklad „bezlepkový chlieb s pšeničnou múkou v náplni" je nezmysel — fail-uj).

V LLM výstupe môže byť **explicitné upozornenie** „obsahuje stopy orechov" — ale len ak `dietary_restrictions` neobsahuje orechy. Inak nezahrnuté jedlo vôbec.

### R4 — JSON schema compliance

LLM výstup musí byť **validný JSON** podľa Pydantic schémy z `backend/src/nutriflow/domain/schemas.py`:

- Žiadne extra polia (`model_config = ConfigDict(extra="forbid")` defaultne).
- Žiadne null v required poliach. Pre nullable použiť explicitné `None` v Pythone, `null` v JSON.
- Numerické polia (kalórie, gramy) musia byť `int` alebo `float`, **nie string s číslom** („250" ako string fail-uje).
- ID-čka (UUID) musia parse-ovať. Žiadne placeholder „xxx-xxx-xxx" v produkčnom drafte.

### R5 — Gramatika a štýl

- **Tykanie:** Aplikácia tyká používateľovi (jeden konzument). Nie „budete" → „budeš".
- **Imperatív v rozumnej miere:** Chef môže napísať „pridaj soľ podľa chuti", ale nie „MUSÍŠ pridať 5g soli" (zbytočne autoritatívne).
- **Žiadne formálne frázy** ako „dovolte mi", „zde najdete". Hovor priamo.
- **Čísla:** v rozpisoch (gramy, kalórie) ponechaj číslice. V naratíve („deň 1", „prvý deň") môžu byť slovom.

### R6 — Žiadne halucinácie ingrediencií

Chef pri pantry-first režime musí používať ingrediencie z `PantryContents`. Ak pridá novú, **musí** ju zahrnúť do `ShoppingListResult`. Žiadne *„štipka kardamómu"* bez položky v shopping list-e.

## Red flags — kedy STOP

Tieto signály v LLM výstupe vyžadujú **okamžité odmietnutie**:

| Signál | Akcia |
|---|---|
| Anglické fráze v naratíve | Reject. Treba prompt update — pravdepodobne anglický few-shot example pretiekol. |
| JSON validation error (Pydantic) | Reject. Logni hodnotu, pridaj negative few-shot do promptu. |
| Jedlo s alergénom z `dietary_restrictions` | Reject + Critic issue. Plán fail-uje, nie kompromis. |
| Field `*_cs` obsahuje anglický text | Reject. Pre tento jeden field problém je pravdepodobne preložená inštrukcia v prompte. |
| Numeric field ako string | Reject. Pydantic `int_from_str` mode má byť explicitne *vypnutý* v `model_config`. |
| Placeholder texty („TODO", „add later", „xxx") | Reject. Pravdepodobne LLM dohrabal token limit a vrátil draft. Pridaj `max_tokens` budget alebo zvýš. |

## Príklad — input/output

### Vstup (prompt fragment)

```markdown
Si Chef agent NutriFlow. Pre uvedený `UserProfile` a `DailyTargets` vygeneruj `WeeklyMealDraft`.

Pravidlá:
- 7 dní × 3 jedlá (raňajky, obed, večera).
- Každé jedlo: české názvy, makrá súčasťou.
- Pantry-first: ak je ingrediencia v `PantryContents`, použi ju.

Výstup je JSON podľa `WeeklyMealDraft` schémy.
```

### ✅ Dobrý výstup

```json
{
  "days": [
    {
      "day_index": 1,
      "meals": [
        {
          "name": "Ovsené vločky s borůvkami a vlašskými ořechami",
          "type": "breakfast",
          "calories": 380,
          "protein_g": 14,
          "carbs_g": 52,
          "fat_g": 12,
          "ingredients": [
            {"name": "ovsené vločky", "quantity": 60, "unit": "g", "from_pantry": true},
            {"name": "borůvky mrazené", "quantity": 80, "unit": "g", "from_pantry": false},
            {"name": "vlašské ořechy", "quantity": 15, "unit": "g", "from_pantry": false}
          ],
          "preparation_cs": "Vločky zalej horkou vodou, povař 3 minuty. Pridaj borůvky a posyp orechami."
        }
      ]
    }
  ]
}
```

**Prečo dobrý:**
- Čeština plynná, žiadne anglicizmy.
- JSON validný.
- `from_pantry` priznačený — Chef využil pantry.
- `preparation_cs` tyká, krátko.
- Makrá ako čísla.

### ❌ Zlý výstup

```json
{
  "days": [
    {
      "day_index": 1,
      "meals": [
        {
          "name": "Oatmeal with blueberries",
          "type": "breakfast",
          "calories": "approximately 380",
          "preparation_cs": "Add oats to hot water and stir. Top with berries.",
          "ingredients": [{"name": "oats", "quantity": 60, "unit": "g"}]
        }
      ]
    }
  ]
}
```

**Prečo zlý:**
- `name` v angličtine.
- `calories` ako string s aproximačným prefixom — fail Pydantic int.
- `preparation_cs` field meno hovorí česky, ale obsah je anglický — porušuje R1.
- `ingredients` chýba `from_pantry` flag.

## Cross-references

- Doménový princíp pre Chef: [`pantry-first-meal-planning`](../pantry-first-meal-planning/SKILL.md)
- Typed handoff: [`agent-handoff-contracts`](../agent-handoff-contracts/SKILL.md)
- Routing: kedy aktivovať tento skill je v [`../../../CLAUDE.md`](../../../CLAUDE.md) routing tabuľke
- Promptá: `backend/src/nutriflow/prompts/*.md`
- Pydantic schémy: `backend/src/nutriflow/domain/schemas.py`

## Definition of Done pre úlohu na ktorej tento skill bežal

- [ ] LLM výstup je validný JSON podľa Pydantic schémy
- [ ] `_cs` polia obsahujú plynnú češtinu (bez anglicizmov mimo akceptovaných)
- [ ] Žiadne jedlo neporušuje `dietary_restrictions`
- [ ] Numerické polia sú čísla, nie strings
- [ ] Žiadne placeholder texty
- [ ] Critic pravidlá z `GOAL.md §14` prejdú (ak je k dispozícii Critic agent)
