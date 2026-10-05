# v0.3 — Investigație reală pe produs

## Obiectiv

v0.3 leagă sursele reale ale unei verificări de produs de obiectul `CaseReport` și de generatorul DOCX introdus în v0.2.

Fluxul țintă este:

`raport stoc → produs → stoc inițial WMS → mișcări WMS → mapare WME → fișă WME → producție → rezultat investigație → CaseReport → DOCX`

## Principii de implementare

- RAW-urile rămân nemodificate.
- Fișierele mari nu sunt încărcate integral în memorie.
- CSV-urile mari sunt citite în chunk-uri și filtrate imediat pe produs.
- XLSX-urile mari sunt citite în mod read-only și sunt reținute numai rândurile relevante.
- WME se filtrează după identificatorul intern rezultat din nomenclator, nu după denumire.
- Dacă maparea WMS ↔ WME lipsește sau este ambiguă, cazul rămâne REVIEW.
- Motorul nu inventează cauza și nu transformă automat o diferență reziduală în eroare reală.
- JSON-ul tehnic și DOCX-ul sunt generate din același rezultat de investigație.

## Intrări CLI v0.3

Pentru investigația completă sunt necesare:

- `--product`
- `--case-id`
- `--period`
- `--stock-report`
- `--opening-stock-wms`
- `--wms-movements`
- `--wme-ledger`
- `--production`
- `--nomenclature`
- `--output-docx`

Opțional:

- `--output-json`
- `--report-date`
- `--engine-commit-sha`
- `--rules-version`

## Limită intenționată a checkpoint-ului

Acest checkpoint extrage cronologia reală pe produs și construiește automat raportul, dar nu declară încă matching documentar complet WMS ↔ WME. Matching-ul operațional, normalizarea semnelor și identificarea automată a cauzei sunt următorul strat al v0.3.

Această limită este deliberată: nu se forțează o reconstrucție cantitativă până când semantica semnului fiecărui tip de operațiune WMS/WME nu este validată pe date reale.
