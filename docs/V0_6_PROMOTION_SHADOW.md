# v0.6 — Non-Golden Shadow & Promotion Safety Gate

Data checkpoint: 2026-10-07

## Scop

După închiderea Golden Gate la 14/14, v0.6 a fost rulat în shadow mode pe un eșantion stratificat de 34 produse care NU fac parte din Golden Case Library.

Eșantionul a inclus:
- diferențe mari, medii și mici;
- valori pozitive și negative;
- cazuri cu operațiuni de producție, livrări, ajustări, mapare raport și opening;
- cazuri aproape de toleranța numerică.

Registry a rămas read-only.

## Rezultat Auto Explain non-Golden

Pe artifactul GitHub Actions run #387:

- total: 34;
- EXACT: 18;
- PARTIAL: 5;
- NONE: 11;
- INCONSISTENT: 0;
- ERROR: 0.

### OPEN-01 persistence guard

Primul shadow non-Golden a arătat că o diferență factuală la deschidere nu este neapărat persistentă.

S-a introdus un guard conservator:
- OPEN-01 contribuie dacă are același sens cu diferența finală și nu o depășește;
- sau dacă face parte dintr-un bridge exact demonstrat prin componente mai puternice (de ex. PROD-02 + PV unic);
- altfel opening-ul rămâne evidence/supporting, fără efect numeric.

După guard:
- Golden Gate a rămas 14/14;
- falsele INCONSISTENT observate în shadow non-Golden au dispărut;
- cazurile neexplicate au rămas NONE/PARTIAL, fără forțare MATCH.

## De ce EXACT nu înseamnă automat promotabil

Auditul non-Golden a arătat cazuri în care o ecuație se închide matematic, dar există familii concurente neînchise.

Exemplu reprezentativ:
- DS099407335: Auto Explain = EXACT prin WME-02 +1;
- dar rămân reziduale mari în production, delivery și generic stock corrections;
- concluzie: EXACT matematic, dar HOLD pentru promovare.

Prin urmare, Auto Explain și Promotion Safety Gate au roluri separate.

## Promotion Safety Gate

A fost adăugat un strat read-only separat:
`assess_auto_explain_promotion(...)`

Principii:
- EXACT este necesar, dar nu suficient;
- nivelul B/C/D nu intră direct în promovare;
- reziduale concurente neexplicate blochează promovarea;
- toleranțele aproape-zero sunt clasificate separat;
- unmatched/warnings sunt păstrate ca semnale de review;
- gate-ul nu schimbă registry, verdictul, WMS sau WME.

### Rezultat pe cele 34 non-Golden — run #391

- HOLD: **26**
- ELIGIBLE_FOR_HUMAN_REVIEW: **4**
- TOLERANCE_MATCH: **4**
- promovări automate: **0**

Cele patru cazuri eligibile pentru review uman:
- DS099904229
- DS099903874
- DS099903805
- DS099903810

Cele patru tolerance matches:
- DS099903451
- 40018
- DS099912575
- DS099904392

## Audit OPEN-01 candidates

### Curate

DS099904229:
- opening WMS 0;
- opening WME 5,525;
- diferență opening = -5,525;
- diferență finală = -5,525;
- WMS net movement 2026 = 0;
- WME net movement 2026 = 0;
- unmatched = 0.

DS099903805:
- opening WMS 0;
- opening WME 1;
- diferență opening = -1;
- diferență finală = -1;
- movement system difference = 0;
- unmatched = 0.

DS099903810:
- opening WMS 0;
- opening WME 1;
- diferență opening = -1;
- diferență finală = -1;
- movement system difference = 0;
- unmatched = 0.

Aceste trei produse sunt candidați buni pentru extinderea viitoare a Golden Library, dar NU au fost promovate automat.

### Rămâne review

DS099903874:
- opening diff = -1;
- final diff = -1;
- movement system difference = 0;
- există totuși document WME non-standard F32046 de -10,5;
- rămâne candidat pentru validare documentară, nu Golden automat.

## Concluzie

v0.6 a trecut două niveluri diferite de control:

1. Golden regression: 14/14 PASS.
2. Non-Golden promotion shadow: numai 4/34 eligibile pentru review uman, 26/34 HOLD.

Acest comportament este intenționat. Motorul nu încearcă să maximizeze numărul de EXACT/promovări, ci să evite falsele explicații.

## Următorul checkpoint recomandat

- validare umană explicită a celor 3 candidați OPEN-01 curați;
- dacă sunt aprobați, extindere Golden Library 14 → 17;
- rerulare Golden Gate 17/17;
- abia apoi evaluare dacă PR #4 poate ieși din draft.

Nu se recomandă încă:
- merge automat;
- update automat REGISTRU_CAZURI;
- activare ca autoritate în locul v0.5;
- ajustări automate WMS/WME.
