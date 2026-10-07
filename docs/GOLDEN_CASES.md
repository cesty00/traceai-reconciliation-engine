# Golden Case Library

## Scop

Golden Case Library este setul controlat de cazuri reale validate manual care protejează TraceAI Reconciliation Engine împotriva regresiilor.

Un Golden Case nu este doar un exemplu. El definește un rezultat așteptat pentru aceeași semnătură logică de intrare:

- diferență finală;
- diferență explicată;
- rezidual;
- nivel de probă;
- cauză;
- reguli contributive;
- pattern operațional;
- condiții care NU trebuie clasificate fals ca sursă a diferenței.

## Reguli de includere

Versiunea 0.2 include numai cazuri care îndeplinesc toate condițiile:

1. verificare manuală detaliată finalizată;
2. nivel de probă A;
3. rezidual cantitativ 0;
4. cauza/componentele sunt documentate;
5. raport sau dovadă oficială disponibilă în Google Drive.

RAW-urile WMS/WME nu intră în GitHub.

## Sursa oficială

Google Drive:
`07_REGULI_SI_CAZURI_ETALON/Golden_Case_Library_TraceAI_v0.2.xlsx`

Manifest machine-readable:
`07_REGULI_SI_CAZURI_ETALON/golden_cases_manifest_v0.2.json`

Schema de contract este:
`config/golden_case.schema.json`.

## Utilizare în v0.6

Pentru fiecare schimbare a motorului:

1. rulează testele unitare;
2. rulează cazurile sintetice scrubbed;
3. compară rezultatele generate cu Golden Case expectations;
4. orice schimbare în `difference / explained / residual / causal pattern` trebuie revizuită explicit;
5. o regulă nouă nu poate transforma un caz în MATCH doar pentru a crește KPI-ul.

## Contract reguli v0.2

Golden Case v0.2 separă explicit:

- `contributing_rules` — reguli cu efect numeric distinct în ecuația WMS−WME;
- `supporting_rules` — reguli de netare, clasificare sau dovadă care NU se adaugă numeric separat.

Golden Gate compară numai regulile contributive. Regulile suport rămân auditabile, dar nu pot produce double counting.

Pentru consumurile `PRODUCTION-IN ↔ BC`, ID-ul canonic este `PROD-03`; denumirea veche `PROD-01` nu se folosește în manifestul v0.2.

## Pattern-uri acoperite în v0.2

- OPEN-01 / diferență de deschidere;
- ADJ-01 / COR STOC WMS-only;
- PROD-03 / BC lipsă în WME;
- PROD-02 / corecție predare sau NP cantitativ diferit;
- DEL-02 / cantitate diferită la livrare;
- GST-04 / PV sau mișcare WME-only;
- R-DER-001 / netare documente derivate și DETERIORATE;
- reversare integrală WMS cu efect net zero;
- diferență persistentă versus diferență temporară;
- sold WME cu mai multe conturi în aceeași gestiune.

## Regresie critică: gestiune + cont

Un sold WME nu poate fi dedus luând ultimul `Balance` doar pe `Warehouse` dacă aceeași gestiune are mai multe conturi active. Soldul trebuie reconstruit pe cheia minimă `Warehouse + Account`, apoi agregat la nivel de gestiune.

Cazul etalon pentru această regresie este `CASE-2026-000042`.

## Principiu

Golden Cases sunt o barieră de siguranță. Dacă motorul nu reproduce un caz etalon, schimbarea trebuie explicată înainte de promovare.
