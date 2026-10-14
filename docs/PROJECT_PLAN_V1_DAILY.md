# TraceAI Control — Plan de proiect / V1 Daily Operations
**Versiune:** 0.1 — 2026-10-14  
**Status:** propunere pentru aprobare; document de guvernanță, nu dovadă de funcționalitate  
**Scop:** operatorul selectează articolul cu diferență WMS–WME; motorul prezintă evenimentele, dovezile, ipotezele și pașii de corecție operațională, fără să efectueze corecții.

## Reguli nenegociabile
1. Manualul WMS–WME v6 din Drive este sursa metodologică. Teste din exporturi reale, păstrarea provenienței, zero MATCH forțat.
2. Separăm: **fapt documentat**, **candidat**, **închidere aritmetică**, **cauză operațională confirmată**.
3. Mișcări fizice vs. documente contabile: recepție, livrare, retur, transfer, BC/NP, PV/ajustare. Niciun transfer intern nu creează stoc agregat.
4. Scope UNKNOWN => REVIEW; nu deducem AGGREGATE din egalitatea soldurilor. Fără conversii presupuse.
5. Interzisă corecția automată în WMS/WME. Aprobarea umană precedă orice acțiune operațională.
6. Nicio funcționalitate marcată DONE fără test reproductibil, CI verde, verificare pe surse reale și criteriile de acceptare semnate.

## Etape cu dependențe și criterii de ieșire

| Etapă | Rezultat livrabil | Criteriu de ieșire | Status |
|---|---|---|---|
| G0 — Guvernanță & CI | roadmap, board/issue tracker, politică PR și CI pentru ramuri feat/** | toate PR-urile active au verificări automate și bază de integrare inteligibilă | BLOCKED |
| G1 — Contractul de date | nomenclator câmpuri WMS/WME, direcții, dată, document, identitate sursă | exporturi reale validate, jurnal rânduri respinse | PLANNED |
| G2 — Scope gestiuni | mapping raport / locații WMS / gestiuni WME, valabilitate și proveniență | cazuri pozitive + negative, confirmare explicită, UNKNOWN rămâne REVIEW | IN PROGRESS (#47, PR #48) |
| G3 — Reconcilieri eveniment | recepții, livrări, retururi, transferuri și lanțuri NT, fără dublări | teste pe 3+ cazuri reale/tip, ambiguități păstrate REVIEW | PARTIAL |
| G4 — Producție & ajustări | BC ↔ PRODUCTION-IN, NP ↔ PRODUCTION-OUT, PV/COR STOC | teste pe cazuri reale, corecțiile nu devin mișcări fizice implicit | PARTIAL (#43/#44) |
| G5 — Daily investigation | selectare articol, timeline, delta pe scope, surse, verdict, acțiuni sugerate | test end-to-end din snapshot+exporturi, explicație demonstrată operatorului | PLANNED |
| G6 — Raport DOCX & pilot | raport conform șablonului din Drive, jurnal aprobări, pilot operațional | 10+ articole reprezentative, revizie umană și fără fals MATCH | PLANNED |
| G7 — Lansare controlată | release candidate, rollback, monitorizare | toate gate-urile verzi; acceptanță operațională explicită | PLANNED |

## Prioritatea imediată și ordinea de lucru
1. **G0/P0:** corectăm declanșarea CI pentru PR-uri intermediare; testăm PR #48 în configurație reală. Nu lăsăm un PR neverificat.
2. **G1/P0:** documentăm schema exactă a datelor și proveniența surselor folosite în test.
3. **G2/P0:** închidem #47 prin mapping explicit și validat; nu promovăm CANDIDAT la VALIDAT pe un singur flux.
4. **G3/P0:** refacem testele pentru #45 în pipeline-ul real, verificând scope și NT în ambele direcții.
5. **G4/G5:** numai după stabilizarea celor de mai sus.
**Politică:** maximum un flux de lucru activ per etapă de integrare; alte PR-uri rămân Draft. Preferăm PR-uri mici, revizuibile, fără modificări direct pe main.

## Backlog existent / dependențe
- PR #43 — checkpoint BC; revizie și CI înainte de integrare.
- PR #44 — poartă pentru atribuirea cauzei PROD-03; revizie și CI.
- Issue #45 / PR #46 — efect economic al mutărilor interne; depinde de validarea scope.
- Issue #47 / PR #48 — registru gestiuni și candidate NT; PR #48 are baza PR #46. **Nu îl fuzionăm înainte ca baza să fie stabilizată.**
- Run #740 a trecut pe PR #46, dar nu validează PR #48.

## Definition of Done (pentru fiecare issue)
- [ ] Contract de intrare/ieșire și scenarii negative documentate
- [ ] Referințe la sursa reală: fișier, hash, perioadă, cod articol, rând/document
- [ ] Test unitar + test de integrare (unde e cazul) + regresii negative
- [ ] CI complet SUCCESS pentru exact commitul livrat
- [ ] Fără false MATCH, fără dublă contabilizare, fără mutații WMS/WME
- [ ] Notă de verificare: ce știm, ce rămâne REVIEW, riscuri, impact
- [ ] Aprobare explicită înainte de merge/release

## Ritm de proiect și raportare
La fiecare checkpoint: **obiectiv**, **ce am verificat**, **ce am schimbat** (link commit/PR), **teste executate și rezultate exacte**, **blocaje**, **următorul pas**. Un issue = o responsabilitate clară, criterii și dovezi; nu marcăm DONE din simpla publicare a unui commit.

## Decizii de arhitectură
- `main` este stabil; integrarea se face în PR-uri mici după CI și revizie.
- Compatibilitatea evenimentelor economice are prioritate față de egalitatea totalurilor.
- Statusurile operatorului disting MATCH/REVIEW/NOT MATCH; diagnosticele candidat nu sunt verdict final.
- Persistăm sursele și argumentele deciziilor, astfel încât raportul să poată fi reprodus.

## Surse
- Manual v6: Google Drive `1wMKcj7KbGhpGyO3M1Ve2rqMsH3j57Dsp`
- Registru candidat: Google Drive `1YAkU9_OuP-_l7y25fGOs67gElVbPanw20S4nzb8S7UQ`
- Repo: `cesty00/traceai-reconciliation-engine`
