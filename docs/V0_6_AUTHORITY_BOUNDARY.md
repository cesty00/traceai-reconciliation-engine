# v0.6 — Authority Boundary

Data checkpoint: 2026-10-07

## Scop

Acest document definește limita de autoritate dintre motorul stabil v0.5 și stratul v0.6 Auto Explain / Promotion Safety Gate.

Obiectivul este ca v0.6 să poată explica și prioritiza cazuri fără să schimbe automat verdictul operațional, registrul sau stocul.

## Autoritatea v0.5

v0.5 rămâne sursa autoritativă pentru:

- `ProductInvestigationResult.verdict`;
- `evidence_level`;
- `cause_code / cause_status`;
- `explained_difference / unexplained_difference` folosite de raportul curent;
- `CaseReport.case_status`;
- payload-ul determinist `build_registry_update(...)`;
- staging / apply-plan pentru REGISTRU_CAZURI.

Orice update al registrului continuă să fie construit din aceste câmpuri și din regulile engine marcate explicit `applied_to_explanation=True`.

## Rolul v0.6

v0.6 poate:

- compune `AutoExplanation` din dovezi deja calculate;
- clasifica rezultatul ca EXACT / PARTIAL / NONE / INCONSISTENT;
- rula Golden Gate;
- rula Promotion Safety Gate;
- produce recomandarea `ELIGIBLE_FOR_HUMAN_REVIEW`, `HOLD` sau `TOLERANCE_MATCH`;
- stoca rezultatul Auto Explain în `result.details["auto_explain"]` pentru audit.

v0.6 NU poate, doar prin aceste rezultate:

- schimba `result.verdict`;
- schimba `result.evidence_level`;
- schimba `result.cause_code`;
- schimba `CaseReport.case_status`;
- rescrie `Regula_aplicata` în registry;
- aplica un registry update;
- modifica WMS sau WME;
- crea ajustări de stoc;
- transforma un HOLD într-un MATCH.

## Contract de registry

`build_registry_update(...)` ignoră `result.details["auto_explain"]` ca autoritate.

Chiar dacă Auto Explain produce:
- status EXACT;
- evidence A;
- rezidual 0;

registry payload-ul rămâne bazat pe verdictul/cauza/evidence/status generate de v0.5 până când o schimbare viitoare de autoritate este aprobată explicit și testată separat.

Acest contract este protejat prin testul:
`test_auto_explain_shadow_cannot_override_registry_authority`.

## Contract Promotion Safety Gate

`assess_auto_explain_promotion(...)` este read-only.

El nu modifică obiectul `ProductInvestigationResult`, registry, WMS sau WME.

Acest contract este protejat prin:
`test_promotion_gate_is_read_only_on_investigation`.

## Regula de promovare

Un rezultat v0.6 poate avansa doar până la review uman dacă:

1. Auto Explain este EXACT;
2. evidence = A;
3. nu există familii reziduale concurente neînchise;
4. Promotion Safety Gate = ELIGIBLE_FOR_HUMAN_REVIEW;
5. nu există ambiguitate documentară relevantă;
6. un om aprobă explicit schimbarea de statut / includerea ca Golden Case.

Nici această aprobare nu autorizează automat o ajustare WMS/WME.

## Golden Case Library v0.3

După aprobarea umană a trei cazuri OPEN-01 independente:
- CASE-2026-000064 / DS099904229;
- CASE-2026-000174 / DS099903805;
- CASE-2026-000165 / DS099903810;

Golden Library are 17 cazuri.

Golden Gate real pe artifactul GitHub Actions run #399:
- 17/17 PASS;
- 17/17 EXACT;
- rezidual 0 pentru toate;
- 0 ERROR.

## Non-Golden promotion shadow

Pe 34 cazuri non-Golden:
- Auto Explain: 18 EXACT / 5 PARTIAL / 11 NONE / 0 INCONSISTENT;
- Promotion Gate: 26 HOLD / 4 ELIGIBLE_FOR_HUMAN_REVIEW / 4 TOLERANCE_MATCH;
- promovări automate: 0.

Acest rezultat confirmă că v0.6 este mai conservator la promovare decât la închiderea matematică.

## Criteriu pentru READY FOR REVIEW

PR #4 poate ieși din draft când:
- CI este verde după testele de authority boundary;
- Golden Gate rămâne 17/17;
- documentația descrie explicit această separare;
- PR nu introduce nicio cale de mutație automată din Auto Explain/Promotion Gate către registry/WMS/WME.

READY FOR REVIEW nu înseamnă activare în producție și nu înseamnă merge automat.
