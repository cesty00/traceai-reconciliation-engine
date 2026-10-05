# TraceAI Reconciliation Engine

Motor Python pentru reconcilierea scriptică WMS ↔ WME, investigarea diferențelor de stoc și identificarea cauzelor.

## Scop

Proiectul urmărește să reconstruiască și să explice diferențele dintre WMS și WME fără a forța potriviri.

Fluxul de verdict este:

`MATCH_DIRECT → MATCH_NORMALIZARE → MATCH_DUPA_NETARE → REVIEW → NOT_MATCH`

Cauza este păstrată separat de verdict.

## Arhitectură

```
Google Drive RAW
   ↓
loaders
   ↓
normalizare
   ↓
evenimente canonice
   ↓
reconciliere / netare
   ↓
investigație pe produs
   ↓
cauză + nivel de probă
   ↓
rezultate / registru cazuri
```

Google Drive rămâne sursa oficială pentru fișierele brute și dovezi. Acest repository conține doar cod, reguli, teste și documentație tehnică.

## Reguli de siguranță a datelor

- Nu se încarcă exporturi WMS/WME brute în GitHub.
- Nu se încarcă fișiere cu clienți, furnizori, stocuri sau trasabilitate reală.
- RAW-ul nu se modifică.
- Regulile candidate nu devin active fără validare.
- Nu se forțează MATCH.

## v0.1

Obiectivul primei versiuni este un audit reproductibil pentru un singur cod de produs:

`stoc inițial → mișcări WMS → mișcări WME → producție → sold calculat → sold raportat → diferențe → operațiuni fără corespondent`

## Structură

- `src/traceai_reconciliation/` — codul motorului
- `config/` — reguli și configurări
- `tests/` — teste unitare și de regresie
- `data/` — doar instrucțiuni; datele reale nu se versioneză
- `docs/` — arhitectură și decizii tehnice
