# Príklad 02 — Skill Invocation

> Ako sa Skill (`czech-llm-output`) aktivuje *pred* prácou a chytí problém, ktorý by inak prešiel.

## Scenár

Užívateľ chce upraviť Chef agent prompt, aby vracal aj prípravné časy.

## Konverzácia

### 👤 Užívateľ

> Pridaj do Chef promptu inštrukciu, že každý recept má obsahovať `preparation_time_min` (čas v minútach).

### 🤖 Claude

> Routing tabuľka: úloha „napísať/vyladiť český LLM prompt" → subagent `prompt-engineer-cs`, skill `czech-llm-output`. Najprv aktivujem skill, potom dispatch.

```
[Skill] czech-llm-output aktivovaný.

Pravidlá pripomenuté:
  R1 — Čeština všade (žiadne anglické termíny v naratíve)
  R4 — JSON schema compliance (preparation_time_min musí byť int, nie string s číslom)
  R5 — Tykanie, žiadne formálne frázy
  R6 — Pravidlá pre kontext NutriFlow
```

> Tiež si pozriem aktuálny Chef prompt cez `filesystem` MCP:

```
mcp__filesystem__read_file("backend/src/nutriflow/prompts/chef.md")
```

```markdown
# Chef agent prompt

Si Chef NutriFlow. Generuj jedlá v češtine podľa schémy WeeklyMealDraft.

## Formát výstupu
- 7 dní × 3 jedlá
- Každé jedlo má makrá (calories, protein_g, carbs_g, fat_g)
- name v češtine
- ingredients ako list

## Pantry first
Preferuj ingrediencie z PantryContents.
```

> Aktivovaný skill ma drží. Pripravím update s rešpektovaním R1+R4:

### Skill catch — pôvodný draft

Než dispatch-nem `prompt-engineer-cs`, skill mi pripomenul **R1: žiadne anglické termíny**. Môj prvý draft bol:

```markdown
## NEW field: preparation_time_min

Every meal must have a `preparation_time_min` field — the prep time in minutes
as an integer.
```

> ❌ Toto poruší R1 (anglický text v inštrukcii). Skill caught it.

### Korigovaný draft

```markdown
## Nové pole: preparation_time_min

Každé jedlo musí mať pole `preparation_time_min` — celkový čas prípravy
v minútach ako celé číslo (int).

Príklady:
- "Vajcia natvrdo" → preparation_time_min: 10
- "Hovězí guláš" → preparation_time_min: 90

Pravidlo: ak nevieš odhadnúť presne, použi konzervatívny odhad (skôr viac
než menej). Číslo musí byť > 0.
```

> Teraz je v češtine, má konkrétne príklady a explicitné typové pravidlo (int, > 0).

### Dispatch subagent

```
[Agent dispatch] prompt-engineer-cs:
  Task: "Update backend/src/nutriflow/prompts/chef.md s novou sekciou
         pre preparation_time_min. Použi nasledujúci text (už prošiel
         skill czech-llm-output review):

         <text vyššie>

         Po update spusti smoke test:
         uv run python -c 'from nutriflow.prompts import load_prompt;
                           print(load_prompt(\"chef.md\")[:500])'
         a over že obsahuje 'preparation_time_min'.

         Skill czech-llm-output: validuj že tvoja zmena dodržuje
         R1 (čeština všade), R4 (numeric ako int), R5 (tykanie)."
```

### 🔧 Subagent `prompt-engineer-cs`

```
[reading chef.md]
[editing — appending nová sekcia po Pantry-first]
[smoke test: prompt loaded, obsahuje preparation_time_min ✓]
✓ done.
```

### 🤖 Claude (späť)

> Chef prompt aktualizovaný. Skill `czech-llm-output` zachytil môj počiatočný draft v angličtine — bez neho by sme do prompta zaviedli inštrukciu v anglickom jazyku, čo by neskôr spôsobilo LLM výstup s anglicizmami.

> Odporúčam ďalší krok: dispatch `test-writer` aby pridal regression test že každý meal v `WeeklyMealDraft` má `preparation_time_min > 0`.

---

## Čo ukazuje tento príklad

1. **Skill chytí chybu PRED kódom** — môj prvý draft bol v angličtine. Bez skill-u by prešiel.
2. **Skill ako pripomienka pravidiel** — nie ako vykonávateľ. Skill je text + ja som vykonávateľ.
3. **MCP tool dodal aktuálny obsah** — `filesystem` ukázal aktuálny stav promptu (nie stale informácia z mojho training).
4. **Skill cross-references s subagent** — subagent dostal v dispatchi explicitnú inštrukciu, ktorý skill rešpektovať. Bez toho by mohol subagent zopakovať moju pôvodnú chybu.

## Súbory dotknuté

- `backend/src/nutriflow/prompts/chef.md` (pridaná sekcia o `preparation_time_min`)
- `backend/src/nutriflow/domain/schemas.py` (predtým: pole `preparation_time_min: int` už pridané do Meal — follow-up úloha)
