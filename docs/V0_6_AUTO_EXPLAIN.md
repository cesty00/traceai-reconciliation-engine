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


## Checkpoint shadow real — 2026-10-07

Golden Case Library curentă: v0.2.3.

Rularea reală folosește artifactul exact trecut prin GitHub Actions și indexul persistent construit din sursele oficiale Drive. Registry rămâne read-only.

Evoluția Golden Gate:
- baseline: 6/14 PASS;
- după politica explicită `opening_absent_means_zero`: 7/14;
- după `WME-02` (PV bridge conservator): 9/14;
- după PROD-02 document residual after reversals: 10/14;
- după PROD-03 persistence/checkpoint + BC basket logic: 12/14;
- după PROD-02 multi-row correction ownership + PV bridge: 13/14;
- după ADJ-01 exact signed correction-chain: **14/14 PASS**.

Checkpoint final shadow:
- 14/14 Golden Cases = `EXACT`;
- 14/14 rezidual = 0;
- 0 ERROR;
- 0 regresii față de cazurile deja verzi;
- 0 update-uri automate în `REGISTRU_CAZURI`;
- sursele RAW nu au fost introduse în GitHub;
- artifact validat: GitHub Actions run #379, head `596542f9108d94e73db499407cd9def9412fb494`.

Regulile suplimentare validate în shadow:
- PROD-03 folosește rezidual persistent, nu suma brută a abaterilor BC;
- split-urile BC pot fi tratate numai când coșul este demonstrabil și univoc;
- PROD-02 acceptă corecții multi-rând numai cu ownership determinist;
- un PROD-02 care traversează temporar ținta este permis doar printr-un bridge PV WME unic care închide exact rezidualul;
- ADJ-01 exact-chain se activează numai dacă `document_residual_total + unconsumed_correction_total` închide exact diferența curentă;
- corecțiile tehnice/TEST rămân în afara ecuației numerice;
- cazurile ambigue rămân REVIEW.

`docs/V0_6_REAL_SHADOW_GAP_MATRIX.md` păstrează istoricul blocajelor și criteriile care au dus la închiderea 14/14.

Pragul minim de 12/14 a fost depășit. Următorul pas nu este activarea directă în producție, ci un checkpoint separat de promovare: rulare shadow pe un eșantion non-Golden, verificare regresii și review uman al schimbării de autoritate față de v0.5.
