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
