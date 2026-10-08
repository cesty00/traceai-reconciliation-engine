# v0.8 — Self-Service Investigation Workflow

## Obiectiv

v0.8 transformă fluxul validat din v0.7 într-un workflow self-service pentru verificarea unui produs/caz, fără a modifica authority boundary.

Utilizatorul trebuie să poată porni o investigație pe cod produs / CASE_ID și să primească:
- reconstrucția diferenței;
- Auto Explain;
- Promotion Safety Gate;
- raport DOCX;
- payload pentru VALIDARE_CAZURI;
- recomandarea următorului pas;
- audit complet al surselor și versiunii motorului.

## Authority boundary — neschimbat

v0.8 NU:
- forțează MATCH;
- aprobă automat cazuri;
- aplică automat modificări în REGISTRU_CAZURI;
- modifică WMS;
- modifică WME;
- face ajustări automate de stoc.

## Flux țintă

`input utilizator → validare surse → investigație → Auto Explain → Promotion Gate → DOCX → staging review → rezultat self-service`

Dacă dovezile sunt insuficiente:
`REVIEW / HOLD / ASTEPTARE_VALIDARE`.

## Milestone 1 — Self-Service Case Runner

Un entry point unic trebuie să accepte cel puțin:
- product_code;
- opțional CASE_ID;
- perioada;
- sursele oficiale;
- output directory.

Output minim:
- `case.json`;
- `case.docx`;
- `registry_update.json`;
- `review_queue.json`;
- `self_service_summary.json`.

## Milestone 2 — Source readiness

Înainte de investigație:
- verifică existența surselor;
- verifică hash-urile și cache/index;
- confirmă cutoff/perioadă;
- oprește controlat rularea dacă lipsește o sursă obligatorie;
- nu înlocuiește automat surse lipsă cu fișiere similare.

## Milestone 3 — Review handoff

Pentru cazuri ELIGIBLE / HOLD / TOLERANCE:
- construiește deterministic payload-ul pentru VALIDARE_CAZURI;
- păstrează `Registry_Action=NONE` până la decizie umană;
- pentru manual evidence, păstrează separat Auto Explain și rezoluția documentară.

## Milestone 4 — Batch self-service

După validarea single-case:
- rulează o listă de produse/cazuri;
- izolează erorile per caz;
- reutilizează indexul;
- produce sumar de lot;
- nu aplică automat rezultate în Drive.

## Acceptanță v0.8 — checkpoint 1

1. CI verde.
2. Golden Gate 17/17 rămâne PASS.
3. Un caz real curat poate fi rulat end-to-end dintr-o singură comandă.
4. Un caz HOLD rămâne HOLD fără override automat.
5. Un caz cu sursă lipsă eșuează controlat și auditabil.
6. Output-urile self-service sunt deterministe.
7. Nicio mutație WMS/WME.
8. Niciun registry apply automat.

## Cazuri pilot recomandate

- DS099904350 — diferență mică, ADJ-01, nivel A.
- 40024 — REAL_MISSING_OPERATION_WME, nivel A.
- 20011 — multi-component manual evidence.
- DS099904370 — PROD-02 + WME-02, manual evidence, caz complex.

## Baseline

v0.7.0 RELEASED:
- release commit `42aac7d8eebbbe879ceee2bda36ba961116a93d4`;
- CI main #444 SUCCESS;
- Golden Gate 17/17 PASS.


## Checkpoint M1 — ACCEPTAT (2026-10-08)

Self-Service Case Runner a fost validat end-to-end pe sursele RAW oficiale.

Pilot real:
- CASE-2026-000187 / DS099904350;
- diferență: -0,300 kg;
- Auto Explain: EXACT;
- nivel probă: A;
- regulă contributivă: ADJ-01;
- rezidual: 0;
- Promotion Safety Gate: ELIGIBLE_FOR_HUMAN_REVIEW;
- Review_Status inițial: STAGED;
- Registry_Action: NONE;
- fără mutații WMS/WME.

Performanță pilot local:
- rulare completă single-case pe RAW: aproximativ 17 secunde;
- WME single-product reader folosește fast-path XML/sharedStrings;
- sursele mari rămân read-only.

Regresie:
- CI PR #7 / run #470: SUCCESS;
- Golden Gate real după hardening: 17/17 PASS;
- nu s-a schimbat ecuația sau setul de reguli contributive pentru niciun Golden Case.

Concluzie:
Milestone 1 este acceptat. PR #7 rămâne draft deoarece v0.8 continuă cu Source Readiness și review handoff.


## Checkpoint M2 — ACCEPTAT (2026-10-08)

Source Readiness a fost întărit și validat pe sursele RAW oficiale.

Contract:
- toate cele 6 surse obligatorii trebuie să existe;
- fișierele goale sunt respinse;
- formatele neacceptate sunt respinse;
- perioada este validată înainte de investigație;
- identitatea fiecărei surse este capturată prin SHA-256;
- dimensiunile și path-urile sunt păstrate auditabil;
- nu există substituire automată/fuzzy a unei surse lipsă;
- orice eroare oprește controlat cazul înainte de investigație.

Pilot DS099904350 după M2:
- EXACT / A / ADJ-01;
- rezidual 0;
- ELIGIBLE_FOR_HUMAN_REVIEW;
- runtime aproximativ 10,5 secunde cu hash cache;
- Registry_Action = NONE;
- toate hash-urile surselor au fost înregistrate în case.json.

CI PR #7 / run #476: SUCCESS.

## Checkpoint M3 — REVIEW HANDOFF VALIDAT (2026-10-08)

Handoff-ul self-service către VALIDARE_CAZURI a fost verificat pe două profile reale:

1. DS099904350 — caz eligibil:
   - ELIGIBLE_FOR_HUMAN_REVIEW;
   - Review_Status = STAGED;
   - Registry_Action = NONE;
   - decizia umană rămâne goală.

2. DS099904370 — caz HOLD:
   - Auto Explain = EXACT;
   - nivel probă B;
   - blocker = EVIDENCE_LEVEL_B_REQUIRES_HUMAN_VALIDATION;
   - Review_Status = STAGED;
   - Registry_Action = NONE;
   - self-service nu reutilizează automat aprobarea/manual evidence dintr-un caz istoric.

Concluzie:
M3 păstrează corect separarea între investigație automată, manual evidence și decizia umană.


## Checkpoint M4 — BATCH SELF-SERVICE ACCEPTAT (2026-10-08)

Batch runner-ul v0.8 a fost validat pe un lot pilot real + eroare sintetică:

- CASE-2026-000187 / DS099904350 → ELIGIBLE_FOR_HUMAN_REVIEW;
- CASE-2026-000008 / DS099904370 → HOLD;
- CASE-V08-ERROR / DS_DOES_NOT_EXIST → ERROR izolat.

Rezultat lot:
- total = 3;
- executate = 2;
- eligible = 1;
- hold = 1;
- error = 1;
- runtime pilot ≈ 28 secunde;
- eroarea sintetică nu a oprit celelalte cazuri;
- fiecare caz valid a produs propriile output-uri self-service;
- fiecare review payload a rămas STAGE_ONLY / Review_Status=STAGED / Registry_Action=NONE;
- batch summary păstrează explicit authority boundary.

CI pentru implementarea batch + CLI: SUCCESS pe PR #7.

## Acceptanță v0.8 — checkpoint 1

Toate criteriile planificate sunt îndeplinite:

1. CI verde.
2. Golden Gate real 17/17 PASS după schimbarea de motor ADJ-01.
3. DS099904350 rulează end-to-end pe RAW oficial și produce EXACT / A / rezidual 0.
4. DS099904370 rămâne HOLD fără override automat.
5. sursa/cazul invalid eșuează controlat și auditabil.
6. output-urile single-case și batch sunt deterministe și structurate.
7. nu există mutații WMS/WME.
8. nu există registry apply automat.

PR #7 poate trece din draft în review. Merge-ul în main rămâne condiționat de CI verde pe head-ul final.
