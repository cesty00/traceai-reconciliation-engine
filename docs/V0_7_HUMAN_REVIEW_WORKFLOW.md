# v0.7 — Human Review Workflow

Data inițiere: 2026-10-07

## Obiectiv

v0.7 transformă rezultatele Auto Explain + Promotion Safety Gate într-un flux operațional de validare umană, fără să modifice authority boundary stabilit în v0.6.

Principiul central:

> explicația automată poate propune, dar numai omul poate aproba; aprobarea nu produce automat update în REGISTRU_CAZURI, WMS sau WME.

## Surse de intrare

v0.7 primește:
- `ProductInvestigationResult`;
- `AutoExplanation`;
- `PromotionAssessment`;
- link de dovezi, dacă există;
- execution_id al rulării.

Nu recalculează investigația și nu schimbă verdictul v0.5.

## Foaia operațională

Workbook:
`CONTROL_RECONCILIERE_WMS_WME`

Sheet:
`VALIDARE_CAZURI`

Coloane:
1. QUEUE_ID
2. CASE_ID
3. Cod_produs
4. Diferenta
5. AutoExplain_Status
6. Nivel_proba
7. Reguli_propuse
8. Promotion_Status
9. Blockers
10. Warnings
11. Prioritate
12. Ce_se_valideaza
13. Link_dovezi
14. Staged_at
15. Execution_ID
16. Reviewer
17. Review_Status
18. Decizie_umana
19. Motiv_decizie
20. Reviewed_at
21. Registry_Action

Foaia `VALIDARE_19` rămâne istoric v0.4 și nu este reutilizată ca sursă autoritativă.

## Statusuri

### Promotion_Status

Este rezultatul automat al Promotion Safety Gate:
- `HOLD`
- `ELIGIBLE_FOR_HUMAN_REVIEW`
- `TOLERANCE_MATCH`

Acest câmp nu este editat manual.

### Review_Status

Workflow uman:
- `STAGED` — item generat de engine;
- `IN_REVIEW` — cineva a început verificarea;
- `APPROVED` — validarea umană a fost favorabilă;
- `REJECTED` — propunerea a fost respinsă;
- `HOLD` — lipsesc documente / există blocaje.

## Decizie umană

Valorile permise:
- `APROBAT`
- `RESPINS`
- `NECESITA_DOCUMENTE`

Reviewer, motivul deciziei și timestamp-ul sunt obligatorii la decizie.

## Reguli de tranziție

### APROBAT

Permis numai dacă:
`Promotion_Status == ELIGIBLE_FOR_HUMAN_REVIEW`

Efect în coadă:
- Review_Status = APPROVED
- Registry_Action = PROPOSE_ONLY

IMPORTANT:
`PROPOSE_ONLY` nu este apply.
Nu există funcție de update REGISTRU_CAZURI în faza v0.7.1.

### RESPINS

- Review_Status = REJECTED
- Registry_Action = NONE

### NECESITA_DOCUMENTE

- Review_Status = HOLD
- Registry_Action = NONE

## Prioritate

- P1 — ELIGIBLE_FOR_HUMAN_REVIEW
- P2 — TOLERANCE_MATCH sau HOLD cu evidence A
- P3 — restul HOLD

Prioritatea ordonează munca; nu schimbă autoritatea.

## Contract tehnic

Generator:
`build_human_review_queue_item(...)`

Payload:
`build_review_queue_payload(...)`

Payload-ul are obligatoriu:
- target.sheet = VALIDARE_CAZURI
- operation = STAGE_ONLY
- registry_mutation_allowed = false
- wms_mutation_allowed = false
- wme_mutation_allowed = false
- human_decision_required = true

Decizia:
`apply_human_review_decision(...)`

Aceasta returnează un obiect nou și nu mută sisteme externe.

## Ce NU face v0.7

v0.7 nu:
- schimbă `ProductInvestigationResult.verdict`;
- rescrie `REGISTRU_CAZURI`;
- aplică `PROPOSE_ONLY`;
- creează ajustări WMS;
- creează documente WME;
- transformă HOLD în MATCH;
- promovează automat un caz Golden.

## Authority boundary

Rămâne identic cu v0.6:
- v0.5 = verdict / cause / evidence / registry authority;
- v0.6 = Auto Explain + Promotion Safety Gate;
- v0.7 = workflow uman de review și audit trail.

Orice pas viitor care aplică o decizie aprobată în registry trebuie să fie un checkpoint separat, cu:
1. PR separat;
2. dry-run;
3. apply-plan;
4. aprobare explicită;
5. readback.

## Faza 1 — criterii de acceptare

- sheet VALIDARE_CAZURI creat;
- payload determinist STAGE_ONLY;
- test că Auto Explain nu poate scrie registry;
- test că HOLD nu poate fi aprobat;
- test că APPROVED produce cel mult PROPOSE_ONLY;
- test că obiectul de investigație rămâne nemodificat;
- CI verde;
- coadă pilot populată din Promotion Safety Gate.

## Următorul pas după faza 1

Populare pilot a cozii cu rezultatele non-Golden deja auditate și verificare manuală a workflow-ului înainte de orice mecanism de sincronizare bidirecțională.
