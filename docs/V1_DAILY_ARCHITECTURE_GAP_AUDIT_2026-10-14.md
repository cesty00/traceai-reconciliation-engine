# Audit de arhitectură — checkpoint de pornire pentru V1 Daily
Data: 2026-10-14. Audit preliminar de cod, NU audit integral al tuturor fișierelor Drive.

## Verificat direct pe ramura PR #55
- `engine.py` (~1582 linii) orchestrează deja matcher-ele receipt, delivery/return, production input, inventory adjustment, generic COR STOC, MOSE, WME residual și detectorul PV.
- `daily.py` (~773 linii) oferă infrastructura fluxului zilnic și gate-uri de publicare.
- `source_index.py` (~685 linii) indexează sursele; `case_builder.py` convertește investigația în CaseReport.
- `docx_report.py` conține secțiunea operatorului, dar acoperă în detaliu mai ales documentele PV.
- Ultimul commit examinat înaintea specificației: 1d33a683; PR #55 era Draft, CI verde.
Aceste observații demonstrează existența modulelor, NU acoperirea exhaustivă a tuturor tipurilor de operațiuni.

## Găuri de arhitectură identificate
**P0 — Ownership economic.** `engine.py` calculează efecte și explicații în mai multe blocuri (`inventory_adjustment_matching`, `generic_stock_corrections`, `delivery_matching`, etc.). Nu este demonstrat un identificator canonic al evenimentului și nici o rezervare globală unică a rândurilor sursă pentru contribuții economice. Risc: dublă contabilizare sau false residual noise. Nu pretind că există un bug în fiecare caz; lipsește o garanție globală.

**P0 — Coverage explicit.** Nu am identificat în aceste module un contract obligatoriu RUN_VERIFIED / NOT_APPLICABLE / BLOCKED_WITH_REASON pentru toate familiile. Un `CI success` nu certifică investigație exhaustivă.

**P0 — Reconstrucție cauzală.** Există reconstrucție sold total și matchere individuale, dar nu este demonstrată o listă unificată de evenimente economice, ordonate cronologic, cu impact delta și diferență cumulată între două checkpoint-uri.

**P1 — Explainability generalizată.** Explicațiile operatorului sunt încă legate de anumite tipuri (în special PV). Trebuie extinse cu un contract comun pentru toate tipurile.

**P1 — Separarea adevărului operațional.** Cazurile numerice închise trebuie separate de aprobarea inventarului, a ajustărilor și a corecțiilor. Fără verdict MATCH bazat doar pe suma egală.

## Plan de implementare incrementală
1. `economic_event_ledger.py` — schemă imutabilă pentru eveniment, rânduri originale (sistem+SHA256+row), cantități, semn, depozit, timp, documente, încredere/validare; fail closed la suprapunere între evenimente economice CONFIRMED.
2. Teste deterministe: rând folosit de două ori => excepție; aceleași date doar în rol de dovadă REVIEW => permis; transfer intern => impact total zero când e justificat; storno legat de factură => o singură contribuție economică.
3. `coverage_manifest.py` — statut pentru fiecare familie; nu poate raporta `COMPLETE` cu familie `BLOCKED`.
4. `causal_reconstruction.py` — ledger ordonat, punct de pornire explicit, comparație cu diferența stoc raportată și diferența rămasă.
5. `operator_explanations.py` — explicații simple din obiecte eveniment, însoțite obligatoriu de dovezi și acțiuni.
6. Integrare graduală în `engine.py` inițial ca shadow-mode read-only: valorile existente NU sunt rescrise până la compararea E2E.
7. Teste reale: cazul 10002 plus cazuri BC/NP, transfer, retur, recepții și ajustări validate de operator; rezultate auditabile și DOCX.

## Decizii de siguranță
- Nu modifica `main`; PR #55 rămâne Draft.
- Nu aplica reconciliere pe simplă egalitate numerică.
- Nu prezenta schema-țintă drept funcție implementată.
- Păstrează `V1_DAILY_RELEASE=NO_GO` până la audit E2E multi-articol.
