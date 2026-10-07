# v0.6 — Real Shadow Gate Result

Data checkpoint: 2026-10-07

## Rezultat final

Golden Case Library: v0.2.3

Shadow run real pe sursele oficiale/indexul persistent:
- total cazuri: 14;
- Golden PASS: **14/14**;
- status Auto Explain: **14/14 EXACT**;
- rezidual numeric: **0 pentru toate cele 14 cazuri**;
- FAIL: 0;
- erori de execuție: 0;
- registry updates automate: 0.

Artifact validat:
- GitHub Actions run: #379;
- head SHA: `596542f9108d94e73db499407cd9def9412fb494`;
- branch: `feature/v0.6-auto-explain`.

## Evoluție

- baseline inițial: 6/14;
- opening absent = 0: 7/14;
- WME-02 PV bridge: 9/14;
- PROD-02 document residual after reversals: 10/14;
- PROD-03 persistence/checkpoint + split BC baskets: 12/14;
- PROD-02 multi-row ownership + exact PV bridge: 13/14;
- ADJ-01 exact signed correction-chain: **14/14**.

## Blocaje închise

### CASE-2026-000014 / 50013

Țintă: -429,4 BUC prin PROD-03.

Închidere:
- diferențele anterioare checkpoint-ului de inventar nu sunt tratate ca persistente;
- neutralizările ulterioare COR STOC cu referință explicită la comandă sunt eliminate din cauză;
- rămân persistente 34904 (-428,4) și 35643 (-1);
- rezultat Auto Explain: **-429,4 PROD-03**, rezidual 0.

### CASE-2026-000026 / 10010

Țintă: -120 BUC = ADJ-01 -118 + PROD-03 -2.

Închidere:
- COR STOC -118 cu motiv explicit non-producție este ADJ-01;
- BC38644/38688 este tratat ca basket split demonstrabil;
- consumul propriu lipsă pentru 38688 + BC35643 lipsă = -2 PROD-03;
- rezultat Auto Explain: **-118 ADJ-01 -2 PROD-03**, rezidual 0.

### CASE-2026-000030 / DS099904006

Țintă: -70 KG = OPEN-01 -1 + PROD-02 -202 + DEL-02 -7 + WME-02 +140.

Închidere:
- reversările/corrections multi-rând sunt agregate numai cu ownership determinist;
- corecțiile explicite la comandă și corecțiile post-NP univoce sunt diferențiate de REVIEW;
- un PROD-02 care traversează temporar ținta este permis numai dacă un singur PV WME închide exact rezidualul;
- rezultat Auto Explain: **-1 OPEN-01 -202 PROD-02 -7 DEL-02 +140 WME-02 = -70**, rezidual 0.

### CASE-2026-000054 / DS099904007

Țintă: -11,8 KG.

Închidere:
- matcherul expune separat toate corecțiile semnate rămase după matching;
- `residual_total` legacy rămâne negative-only pentru compatibilitate;
- Auto Explain folosește un lanț ADJ-01 numai dacă `document_residual_total + unconsumed_correction_total` închide exact diferența curentă;
- rezultat Auto Explain: **-11,8 ADJ-01**, rezidual 0.

## Reguli de siguranță păstrate

- Golden Gate nu a fost relaxat pentru a crește procentul de PASS.
- Nu se însumează arbitrar PV/F sau COR STOC.
- WME-02 acceptă numai un PV unic care închide exact rezidualul.
- PROD-02 folosește ownership determinist și elimină ordinele complet reversate.
- PROD-03 folosește persistență cronologică/checkpoint și confirmare producție.
- Corecțiile `TEST` nu intră în ecuația numerică.
- Cazurile ambigue rămân REVIEW.
- Registry rămâne read-only în shadow mode.
- Datele RAW nu intră în GitHub.

## Concluzie

Pragul minim de promovare tehnică 12/14 a fost depășit: **14/14**.

Acest rezultat validează Auto Explain pentru trecerea la următorul checkpoint de promovare, dar nu autorizează încă:
- activarea ca autoritate în locul v0.5;
- update automat de registry;
- corecții automate WMS/WME;
- merge fără review.

Următorul pas corect: shadow pe un eșantion non-Golden + review uman al regulilor înainte de orice activare.
