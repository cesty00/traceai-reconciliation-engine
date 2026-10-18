# TraceAI Control — V1 Daily | Baseline integrat de cerințe și testare
Data: 2026-10-14 · Status: SPECIFICAȚIE / NU ESTE APROBARE DE LANSARE
Repo: cesty00/traceai-reconciliation-engine · PR #55 (Draft)

## Contractul produsului
Operatorul introduce un articol. TraceAI parcurge automat toate operațiunile relevante WMS ↔ WME, reconstruiește cronologic diferența, explică evenimentele care i-au modificat valoarea, arată dovada până la rândul fizic din fișier și generează un raport DOCX inteligibil inclusiv unui începător. Nu execută corecții WMS/WME; operatorul validează justificarea operațiunilor.

## Cerințe funcționale obligatorii
**REQ-01 — Surse și identitate.** Stoc WMS/WME, deschidere WMS, trasabilitate WMS, fișă magazie WME, producție, rețete, nomenclator, facturi/avize/PV unde sunt disponibile. Pentru fiecare: SHA256, versiune, interval, mapare articol/UM/gestiune, SourceRowNumber fizic. Nu publica sursele confidențiale în GitHub.

**REQ-02 — Acoperire integrală.** Sold inițial; recepții/FE/F/NIR; livrări/AE/facturi/storno; retururi; transferuri interne și MOSE/NT; producție BC/NP; ajustări COR STOC și INV-PLS/INV-MIN; inventare/PV; operațiuni speciale STATUS_ONLY / DETERIORATE / PROTAN / MOSTRE / packing. Fiecare familie primește RUN_VERIFIED, NOT_APPLICABLE sau BLOCKED_WITH_REASON. Un caz nu este explicat integral dacă există familii relevante neexecutate.

**REQ-03 — Eveniment economic și unicitate.** Normalizează semnul, documentul, articolul, UM, data și gestiunea. Evenimentul poate conține mai multe rânduri și documente. Un rând original nu poate contribui de două ori la impactul economic confirmat; listele de dovezi pot repeta referința, dar impactul nu. Factura nu implică automat o a doua mișcare fizică.

**REQ-04 — Reconstituirea diferenței.** Difference = WMS − WME pentru reconcilierea sistemelor; inventarele fizice folosesc formula distinctă din procedura de inventariere. Calculează Δ(event)=Σsigned_WMS−Σsigned_WME, incluzând soldul inițial, compensări, anulări și intrări/ieșiri, pe perioada corectă. Comparație obligatorie cu soldul raportat. Ultimul moment de aliniere scriptică este un checkpoint de calcul, NU validare implicită a inventarului fizic.

**REQ-05 — Match conservator.** MATCH numai cu identificare documentară/economică demonstrată; nu forța match doar pe dată și cantitate. Distinge: impact net confirmat, legătură documentară confirmată și justificare umană. REVIEW dacă lipsește dovada; nu converti automat REVIEW în MATCH sau în corecție de stoc.

**REQ-06 — Reguli operaționale existente.** RECEIPT/DELIVERY/RETURN_IN prioritare. WME „-” poate indica retur; WMS recepție „-1” poate indica retur de recepție; RET_WME / WME<doc>-1 tratate după tipologie și dovezi; normalizează prefix SFA numai unde regula este validată; MOSE/TRANSFER_MOSE și transferuri între gestiuni nu modifică automat stocul total; BC consum și NP predare, cu probă din producție; unități/baxuri convertite doar cu echivalență demonstrată și aprobată. Nu generaliza raportul 8:1 între articole.

**REQ-07 — Documente și compensări.** Un PV poate fi împărțit pe mai multe rânduri. O sumă egală între WMS și WME nu dovedește singură identitate documentară. Compensările ± care se anulează nu explică o diferență finală. Documentele cu decalaj de dată sunt legate numai cu regulă justificată; nu aplica regulă de asociere dacă există mai mulți candidați sau gestiuni ambigue.

**REQ-08 — Explicație pentru începător.** Pentru fiecare abatere: (1) ce s-a întâmplat, (2) ce spune WMS, (3) ce spune WME, (4) unde diferă, (5) cum modifică diferența cumulată, (6) ce documente și rânduri trebuie deschise, (7) pașii concreți de verificare, (8) ce va decide operatorul, (9) ce NU este dovedit. Include legendă BC/NP/PV/FE/AE/NT/COR STOC, REVIEW/MATCH/NOT_MATCH. Două niveluri: rezumat executabil și anexă integrală.

**REQ-09 — Validare umană și control al lansării.** HUMAN_VALIDATION_PENDING nu înseamnă cauza matematică necunoscută; cauză matematic documentată nu echivalează cu legitimitate aprobată. Nu modifica WMS/WME, nu promova automat cazuri/PR și nu publica rezultate sensibile. Release V1_DAILY_RELEASE=NO_GO până la E2E real, fără regresii.

**REQ-10 — Audit și acces.** Snapshot surse, SHA256, versiunea regulilor, commit, linia sursă, traseu de concluzie, motive pentru excludere/echivalare, rezultat al validării. Fără inventare sau documente brute publicate în repo.

## Cazuri reale de acceptanță (nu fixture-uri inventate drept dovezi)
- CASE-10002: la 25.06.2026 ultima aliniere scriptică; 26.06 3× COR STOC −450 -> −1350; 30.06 +1 -> −1349; 08.07 F 6009708 −232 WME -> −1117; 23.07 PV 2557 −245 WME -> −872. Operatorul decide realitatea inventarului; fiecare legătură și impact trebuie justificată pe rânduri-sursă; nu marca automat MATCH.
- CASE-10002/PV2676: 07.10.2026 WMS −145, −450, −450; WME −856.9999, −188.0001; totaluri −1045/−1045, efect net 0 dacă al treilea rând WMS aparține PV; rândul fără referință explicită rămâne REVIEW până la confirmare.
- CASE-10002/PV2265: aceeași cantitate, dar gestiuni diferite: REVIEW, nu neutralizare forțată.
- CASE-10002/BC: diferențe brute WMS/WME și conversii aparente, dar cantitatea efectiv consumată se stabilește din documentele operaționale și validarea umană; nu confunda reziduul BC cu −872.
- CASE-DS099904475 / comanda 0023462_DC: consum fizic confirmat 50 cutii pentru 400 caserole; în WMS înregistrate eronat 400 cutii. Regresie pentru corecția de operator, nu conversie automată globală.
- CASE-MOSE: transferuri și retururi între depozite; protecție împotriva numărării unei mutări interne ca livrare externă.
- CASE-PRODUCTION: BC și NP pe comandă/produs/lot; lot, UM, rețetă, preț și consum trebuie verificate distinct.
- CASE-RECEIPT-DELIVERY: FE/F/AE, retur, stornări și documente cu sufix -1/-2; compară și documentele fără corespondent.

## Contract de rezultat per articol (de implementat)
{
  "source_identity": {"product_code": "...", "wme_ids": [], "warehouse_scope": []},
  "coverage": [{"family": "RECEIPT", "status": "RUN_VERIFIED|NOT_APPLICABLE|BLOCKED_WITH_REASON", "reason": "..."}],
  "opening": {"wms": null, "wme": null, "aligned_at": null, "physical_inventory_validated": false},
  "causal_events": [{"event_id": "...", "wms_source_rows": [], "wme_source_rows": [], "delta_wms_minus_wme": null, "cumulative_difference": null, "evidence_status": "CONFIRMED|REVIEW"}],
  "reconciliation": {"reported_difference": null, "reconstructed_difference": null, "reconstruction_gap": null},
  "operator_actions": [{"priority": "P1", "what_happened": "...", "wms_evidence": [], "wme_evidence": [], "impact_explained": "...", "operator_steps": [], "uncertainties": []}],
  "result": {"mathematical_reconstruction": "COMPLETE|PARTIAL|BLOCKED", "human_validation": "PENDING|VALIDATED|REJECTED", "verdict": "REVIEW"},
  "audit": {"source_sha256": {}, "engine_commit": "...", "rules_version": "..."}
}
Aceasta este o schemă-țintă, nu o afirmație că toate câmpurile există deja în aplicație.

## Gate-uri de acceptanță
A: catalogul tuturor familiilor implementat + execuția observabilă per familie.
B: verificare identitate articol/UM/gestiune + trasabilitate până la rândul original.
C: ownership economic per rând; nicio dublă contabilizare între module.
D: reconstrucție cronologică a diferenței cu Δ explicat și prag de toleranță validat.
E: test E2E 10002 cu explicația celor patru evenimente, PV2676 impact zero condițional și PV2265 REVIEW.
F: raport DOCX + interfață Daily în limbaj operațional, inclusiv pași de verificare.
G: regresie multi-articol, CI integral, fără promovare automatizată pe rezultate incerte.
Orice gate absent => V1_DAILY_RELEASE=NO_GO.

## Ordinea inginerească de lucru
1. Inventory audit GitHub + Drive + surse; mapa implementat / testat / nevalidat.
2. Event ledger canonical și ownership per SourceRowNumber, fără schimbarea matcherelor existente.
3. Coverage orchestrator pentru toate familiile, cu BLOCKED explicite.
4. Causal reconstruction de la ultimul sold aliniat și/sau sold inițial.
5. Operator explanation builder + rapoarte DOCX și UI.
6. E2E comparativ 10002 plus alte cazuri reale aprobate de utilizator.
7. Pilot în mod doar-citire; abia apoi evaluare pentru release.

## Constrângeri de proprietate intelectuală
Dezvoltarea este proiectul independent al autorului; distribuția către companie se negociază separat, fără transfer implicit de proprietate. Orice licență sau separare între cod și date necesită verificare juridică înainte de implementare comercială.
