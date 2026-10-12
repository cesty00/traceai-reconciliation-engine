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


## v0.4

v0.4 stabilizează motorul pentru utilizare repetată pe produse reale și extinde matching-ul operațional fără a forța închiderea cazurilor:

- cache SHA-256 pentru sursele mari și index SQLite reutilizabil;
- parser XML streaming pentru fișa WME XLSX;
- indexare reală validată pe 343.070 rânduri WMS, 243.151 WME și 72.255 producție;
- RECEIPT: `IN → FE` și `TRANSFER_CG → NT`;
- DELIVERY: normalizare `SFA/RET_SFA/AV_WMS`, excluderea transferurilor, netarea `ANULARE COMANDA` și a lanțurilor `-1/-2/-1-1`;
- reconcilierea rândurilor raportului de stoc cu gestiunile WME, inclusiv GST-02/GST-03 pentru zone cu `QuantityERP=0`;
- matcher `TRANSFER_MOSE ↔ NT WME` la nivel de coș complet multi-produs, cu netare `_DEL_` și fallback conservator;
- contract determinist `registry_update` pentru sincronizarea cu `REGISTRU_CAZURI`, fără credențiale Google în motor;
- status diferențiat: `IN_ANALIZA` pentru cazuri cu rezidual neexplicat și `ASTEPTARE_VALIDARE` pentru cazuri explicate integral dar încă în REVIEW uman.

v0.4 păstrează regulile de siguranță: RAW-urile nu sunt versionate, MATCH nu este forțat, iar regulile care nu contribuie efectiv la explicație rămân doar dovezi tehnice și nu sunt scrise ca `Regula_aplicata` în registru.

## Obiectivul fluxului pe produs

`stoc inițial → mișcări WMS → mișcări WME → producție → sold calculat → sold raportat → diferențe → cauză → recomandări → DOCX`

## Structură

- `src/traceai_reconciliation/` — codul motorului
- `src/traceai_reconciliation/reports/` — model și generator DOCX
- `config/` — reguli și schema raportului
- `tests/` — teste unitare și de regresie
- `data/` — doar instrucțiuni; datele reale nu se versioneză
- `docs/` — arhitectură și șablonul oficial de raport


## Golden Case Library

Începând cu hardening-ul final v0.5, proiectul are o bibliotecă de cazuri etalon validate manual. Contractul este documentat în `docs/GOLDEN_CASES.md`, iar schema machine-readable este `config/golden_case.schema.json`.

Scopul este ca v0.6 și versiunile ulterioare să poată automatiza explicarea cauzelor fără să regreseze cazurile deja demonstrate.


## v0.7 — Human Review Workflow

v0.7 adaugă fluxul controlat de validare umană peste Auto Explain și Promotion Safety Gate:

- coadă operațională `VALIDARE_CAZURI`;
- stări auditabile `STAGED / IN_REVIEW / APPROVED / REJECTED / HOLD`;
- decizii umane `APROBAT / RESPINS / NECESITA_DOCUMENTE`;
- `Manual Evidence Resolution` pentru cazuri HOLD cu dovezi documentare nivel A și rezidual 0;
- separarea strictă între Auto Explain, dovada manuală și aprobarea finală;
- `Registry_Action=PROPOSE_ONLY` după aprobare; fără apply automat;
- nicio mutație automată WMS/WME;
- Golden Gate real: 17/17 cazuri etalon PASS;
- CI pe `main` după merge: GitHub Actions #442 SUCCESS.

Release commit de bază: `752bfbbb30dcebd66648e0c82daaf9e58983316c`.


## v0.8 — Self-Service Investigation Workflow

v0.8 introduce rularea controlată self-service peste motorul validat v0.7:

- single-case runner: surse → investigație → Auto Explain → Promotion Gate → DOCX → review queue;
- output-uri standard: `case.json`, `case.docx`, `registry_update.json`, `review_queue.json`, `self_service_summary.json`;
- Source Readiness fail-closed cu validarea existenței, dimensiunii, formatului, perioadei și identității SHA-256;
- fast-path WME single-product pe XML/sharedStrings pentru rulări pe RAW oficial;
- handoff determinist către `VALIDARE_CAZURI`, fără aprobare automată;
- batch self-service cu izolare de eroare per caz și sumar de lot;
- ADJ-01 poate primi nivel A numai pentru o corecție generică izolată, exactă și demonstrată independent de movement bridge;
- Golden Gate real 17/17 PASS după schimbarea de motor;
- pilot single-case DS099904350: EXACT / A / ADJ-01 / rezidual 0 / ELIGIBLE_FOR_HUMAN_REVIEW;
- pilot batch: eligible 1 / hold 1 / error izolat 1;
- fără registry apply automat și fără mutații WMS/WME.

Feature merge commit de bază: `3e4363e4ff3a1b40032789de3848a5e4c6968306`.


## v0.9 — Daily Operations Readiness

v0.9 transformă motorul self-service validat în v0.8 într-un flux zilnic controlat și repetabil:

- profil YAML pentru sursele zilnice și manifestul de cazuri;
- validare fail-closed înainte de analiză;
- SHA-256 pentru identitatea surselor;
- manifest determinist de rulare și semnătură completă;
- idempotency/reuse pentru rulări identice;
- clasificare delta între rulări: `NEW / CHANGED / UNCHANGED`;
- politici conservative: `ANALYZE / REANALYZE_SOURCE_CHANGED / REUSE_SAFE`;
- Daily Release Gate în GitHub Actions;
- contract CI pentru biblioteca oficială de 17 Golden Cases;
- release-candidate verdict gate agregat;
- fără aprobare automată, fără registry apply automat și fără mutații WMS/WME.

Feature merge commit de bază: `81f1fa005208d532d80d0a810465dae5a9d1ddcc`.


## v0.10 — Daily Operator View

v0.10 adaugă un rezultat compact, read-only, orientat către operator pentru utilizarea zilnică:

- cauză, reguli, nivel de probă și rezidual;
- țintă de corecție și acțiune recomandată;
- output standard `daily_operator_result.json`;
- separare explicită între diferențe operaționale și diferențe de mapare/raport;
- nicio mutație automată WMS/WME și fără forced MATCH.

Contractele de versiune sunt centralizate în `src/traceai_reconciliation/version.py`:
`ENGINE_VERSION`, `RULESET_VERSION`, `DAILY_RUN_SCHEMA_VERSION` și
`OPERATOR_OUTPUT_SCHEMA_VERSION`.
