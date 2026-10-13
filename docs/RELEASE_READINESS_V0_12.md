# v0.12 Release Readiness

Acest document definește criteriile minime pentru promovarea TraceAI Reconciliation Engine către un release intern v0.12.

## Release blockers

Release-ul este blocat dacă oricare dintre condițiile de mai jos nu este îndeplinită:

- suita completă `pytest` este verde;
- Golden Gate oficial este verde;
- DAILY release gate este verde;
- toate artefactele obligatorii DAILY sunt validate înainte de succes sau reuse;
- Run Store poate migra până la schema curentă;
- `snapshot_at` rămâne explicit și nu este înlocuit cu `started_at`, file mtime sau report date;
- authority boundary rămâne fail-closed:
  - human decision required;
  - automatic approval disabled;
  - registry apply disabled;
  - WMS mutation disabled;
  - WME mutation disabled;
- versiunile de package și engine sunt sincronizate;
- contractele JSON operator/self-service sunt versionate explicit.

## Release candidate sequence

1. Freeze funcțional: fără reguli de business noi în release candidate.
2. Rulează suita completă și toate gate-urile CI.
3. Rulează testele dedicate de release readiness.
4. Actualizează versiunea engine/package la versiunea candidate.
5. Actualizează README/changelog pentru release.
6. Creează tag-ul candidate numai după CI verde pe `main`.
7. Rulează un pilot operațional controlat pe date reale, fără mutații automate.
8. Promovează la release intern numai după validarea pilotului.

## Reguli de siguranță

Release readiness nu schimbă regulile de reconciliere și nu autorizează mutații WMS/WME. Un caz insuficient demonstrat rămâne `REVIEW / ASTEPTARE_VALIDARE`.


## Candidate version

Release candidate version: `0.12.0`

Version bump-ul trebuie considerat valid numai dacă workflow-ul complet de pe branch și apoi de pe `main` rămâne verde.


## Technical sign-off checkpoint

Technical validation is complete on commit `e784299eeb3e0063bad7c9ab5321db168f3bcb2b`.

Evidence and pilot conclusions are recorded in:

`docs/RELEASE_SIGNOFF_V0_12.md`

Current state: **TECHNICALLY ACCEPTED — PENDING HUMAN RELEASE APPROVAL**.
