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
