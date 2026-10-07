# v0.6 — Real Shadow Gap Matrix

Data checkpoint: 2026-10-07

## Rezultat curent

Golden Case Library: v0.2.3

Shadow run real pe sursele oficiale/indexul persistent:
- total cazuri: 14;
- EXACT / Golden PASS: 10;
- FAIL: 4;
- erori de execuție: 0;
- registry updates automate: 0.

Progres observat:
- baseline inițial: 6/14;
- după politica explicită opening absent = 0: 7/14;
- după WME-02 PV bridge: 9/14;
- după PROD-02 document residual after reversals: 10/14.

## Cazuri rămase

### CASE-2026-000014 / 50013

Țintă: -429,4 BUC prin PROD-03.

Blocaj:
- există mai multe reziduale PRODUCTION-IN/BC în perioadă;
- simpla sumare a rezidualelor produce -42, nu cauza persistentă;
- 34904 (-428,4) și 35643 (-1) sunt persistente;
- 29279/30275 sunt tranzitorii;
- 38457 este compensat ulterior.

Necesitate:
- matcher PROD-03 cu persistență cronologică/checkpoint, nu sumă brută.

### CASE-2026-000026 / 10010

Țintă: -120 BUC = ADJ-01 -118 + PROD-03 -2.

Blocaje:
- COR STOC -118 din ULMA este clasificat de matcherul vechi ca PROD-02, deși contextul este corecție stoc/material;
- BC38644/38688 trebuie analizate ca un coș multi-produs: împreună reproduc 0038644_AE și lasă consumul propriu 0038688_AE lipsă.

Necesitate:
- ownership explicit COR STOC: producție vs ajustare generică;
- basket-level PROD-03 pentru split BC.

### CASE-2026-000030 / DS099904006

Țintă: -70 KG = OPEN-01 -1 + PROD-02 -202 + WME-02 +140 + DEL-02 -7.

Blocaj:
- producția include multiple ordine WMS-only reversate pe mai multe rânduri;
- matcherul curent de reversări unu-la-unu nu reconstruiește toate coșurile;
- PROD-02 persistent -202 nu poate fi izolat încă automat;
- PV2301 +140 devine eligibil WME-02 numai după izolarea PROD-02.

Necesitate:
- effective production by order/basket după toate reversările și corecțiile.

### CASE-2026-000054 / DS099904007

Țintă: -11,8 KG.

Blocaj:
- două corecții de producție relevante (-19 +7,2) sunt amestecate cu alte corecții/reversări;
- matcherul generic vede numai -2,4 din alte operațiuni;
- este necesară reconstruirea lanțului de corecție, nu suma tuturor COR STOC.

Necesitate:
- correction-chain ownership + persistence.

## Reguli de siguranță

- Golden Gate nu se relaxează pentru a crește procentul de PASS.
- Nu se însumează arbitrar PV/F sau COR STOC pentru a închide o diferență.
- WME-02 acceptă doar un PV unic care închide exact rezidualul după neutralizări unu-la-unu.
- PROD-02 document residual se folosește numai după eliminarea ordinelor complet reversate.
- Registry rămâne read-only în shadow mode.
- Datele RAW nu intră în GitHub.

## Următorul prag

Înainte de orice promovare a Auto Explain din shadow mode:
- minimum 12/14 Golden PASS;
- 0 regresii pe cele 10 cazuri deja verzi;
- 0 ERROR;
- fiecare nouă regulă are test sintetic + shadow evidence;
- cazurile rămase sunt păstrate REVIEW dacă dovada nu este suficientă.
