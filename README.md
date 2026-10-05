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
rezultate / registru cazuri + DOCX
```

Google Drive rămâne sursa oficială pentru fișierele brute și dovezi. Acest repository conține doar cod, reguli, teste și documentație tehnică.

## Reguli de siguranță a datelor

- Nu se încarcă exporturi WMS/WME brute în GitHub.
- Nu se încarcă fișiere cu clienți, furnizori, stocuri sau trasabilitate reală.
- RAW-ul nu se modifică.
- Regulile candidate nu devin active fără validare.
- Nu se forțează MATCH.

## v0.2

Motorul include generatorul automat DOCX pentru fiecare caz verificat. Raportul conține:

- rezumat executiv;
- diferență inițială / explicată / neexplicată;
- surse și dovezi;
- rezultat reconciliere;
- constatări și cauză;
- recomandări;
- verdict și validare umană;
- jurnal cronologic;
- operațiuni fără corespondent;
- trasabilitatea concluziei;
- parametri tehnici ai execuției.

Generatorul validează înainte de salvare că:

`diferență inițială = diferență explicată + diferență neexplicată`

în toleranța configurată.


## v0.3

Motorul include investigația reală end-to-end pe produs:

- filtrare eficientă a surselor WMS/WME/producție;
- reconstrucția soldurilor și separarea diferenței de deschidere;
- matching producție `PRODUCTION-OUT ↔ NP` și `PRODUCTION-IN ↔ BC`;
- netarea livrărilor/retururilor înainte de comparația cu AE;
- identificarea reversărilor și a corecțiilor WMS reziduale;
- fluxuri speciale candidate tratate conservator;
- raportarea mișcărilor WME non-standard fără a forța legături documentare;
- `ProductInvestigationResult → CaseReport → JSON + DOCX` într-o singură execuție CLI.

v0.3 a fost validat end-to-end pe trei cazuri reale independente. Datele reale nu sunt versionate în repository; testele păstrează doar tipare sintetice/regresii scrubbed.

## Obiectivul fluxului pe produs

`stoc inițial → mișcări WMS → mișcări WME → producție → sold calculat → sold raportat → diferențe → cauză → recomandări → DOCX`

## Structură

- `src/traceai_reconciliation/` — codul motorului
- `src/traceai_reconciliation/reports/` — model și generator DOCX
- `config/` — reguli și schema raportului
- `tests/` — teste unitare și de regresie
- `data/` — doar instrucțiuni; datele reale nu se versioneză
- `docs/` — arhitectură și șablonul oficial de raport
