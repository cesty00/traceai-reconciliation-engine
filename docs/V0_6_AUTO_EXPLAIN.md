# v0.6 — Auto Explain Engine

## Obiectiv

v0.6 transformă rezultatele tehnice demonstrate în ecuații explicite ale diferenței WMS↔WME, fără a inventa cauze și fără a executa corecții în sisteme.

Fluxul țintă:

`matching determinist → componente demonstrate → Auto Explain → Golden Case regression → validare umană → recomandare`

## Contract de siguranță

Auto Explain:

- nu citește RAW pentru a ghici cauza;
- nu promovează automat componente REVIEW;
- folosește implicit numai componente `CONFIRMED`;
- componentele `PROBABLE` pot fi incluse numai explicit;
- respinge ID-uri duplicate pentru a preveni double counting;
- nu schimbă singur verdictul cazului;
- nu autorizează ajustări WMS/WME;
- păstrează rezidualul vizibil.

## Status explicație

- `EXACT` — suma componentelor este egală cu diferența raportată în toleranță;
- `PARTIAL` — explicația reduce rezidualul, dar nu îl închide;
- `NONE` — nu există componente eligibile;
- `INCONSISTENT` — componentele selectate măresc abaterea sau nu pot descrie ținta.

## Faza 1

Implementată în primul checkpoint v0.6:

- `ExplanationComponent`;
- `AutoExplanation`;
- `compose_explanation(...)`;
- componentă factuală `OPEN-01`;
- teste sintetice inspirate din Golden Cases:
  - multi-componentă cu semne opuse;
  - opening-only;
  - PROBABLE exclus implicit;
  - timing/non-contributing exclus;
  - protecție duplicate;
  - explicație inconsistentă.

## Faza 2

Următorul checkpoint:

1. adaptoare pentru matcher-ele existente:
   - production;
   - production input / BC;
   - delivery;
   - generic stock correction;
   - special status / WME-only;
2. generare `explanation_components` în `ProductInvestigationResult.details`;
3. comparație automată cu Golden Case expectations;
4. fără modificarea automată a registrului înainte de validare.

## Golden Case gate

Orice componentă nouă trebuie să treacă:

`unit tests → scrubbed regression → Golden Case comparison → review`.

Obiectivul nu este creșterea artificială a procentului MATCH, ci reducerea rezidualului prin explicații auditabile.


## Golden Case gate implementat

Checkpoint-ul curent include un gate read-only pentru compararea Auto Explain cu așteptările etalon:

- `GoldenExpectation` definește diferența, explicatul, rezidualul, regulile și statusul așteptat;
- `compare_auto_explanation(...)` produce PASS/FAIL și enumeră exact regresiile;
- `summarize_golden_gate(...)` agregă rezultatele unui lot de Golden Cases;
- toleranța numerică este explicită;
- gate-ul nu modifică investigația, registrul sau sursele.

Auto Explain rulează în prezent în **shadow mode** în `investigate_product` și este salvat în `result.details["auto_explain"]`. Rezultatele v0.5 rămân autoritare până când Golden Case gate este rulat cu succes pe biblioteca reală.
