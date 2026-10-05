# v0.4 — Stabilizare și integrare registry

## Obiectiv

v0.4 transformă fluxul v0.3 într-un motor reutilizabil pentru verificări repetate pe produse reale, cu accent pe performanță, reducerea falselor diferențe și sincronizarea auditabilă a rezultatului în registrul de cazuri.

## Performanță

Sursele operaționale mari pot fi indexate local în `.traceai_cache`:

- WMS: 343.070 rânduri;
- WME: 243.151 rânduri;
- producție: 72.255 rânduri.

Pe setul real validat, construcția completă a indexului durează aproximativ 21 secunde, iar reutilizarea indexului existent este practic instantanee. WME XLSX este indexat prin XML streaming direct din containerul XLSX pentru a evita costul mare al iterării openpyxl.

## Matching operațional extins

### RECEIPT

- `IN... WMS → FE pozitiv WME`, după `Document intrare` și cantitate agregată;
- `TRANSFER_CG... WMS → NT pozitiv WME`;
- `RET_WME/RET_SFA`, `TRANSFER_MOSE` și lanțurile derivate rămân în familiile lor dedicate.

### DELIVERY și documente derivate

- prefixurile `SFA`, `RET_SFA`, `WME`, `WMS`, `AV_WMS` sunt normalizate;
- livrările `TRANSFER_*` sunt excluse din comparația cu AE;
- `ANULARE COMANDA` și `*_DEL_<UUID>` sunt netate fără dublarea unei livrări pozitive deja existente;
- lanțurile `-1/-2/-1-1` sunt normalizate către documentul de bază și comparate după netare;
- AE WME-only sunt raportate separat și nu modifică automat rezidualul DELIVERY.

Validarea globală a documentelor derivate a acoperit 182 perechi produs + document de bază; 157 se închid exact după netare față de AE WME, iar excepțiile rămân REVIEW.

### TRANSFER_MOSE

Matcherul dedicat:

1. normalizează ordinul de bază și netează `_DEL_`;
2. folosește prioritar `Document intrare` când există;
3. cu index activ, compară coșul complet multi-produs și direcția transferului;
4. acceptă fallback pe dată/lag scurt numai când relația este univocă;
5. păstrează `NEPROCESAT`, lipsa documentului și ambiguitățile în REVIEW.

Validarea globală a identificat 551 transferuri WMS efective și 550 documente NT WME; 547 transferuri s-au potrivit exact la nivel de coș complet.

## Maparea raportului de stoc

v0.4 aplică GST-02/GST-03 la nivel de rând de gestiune:

- `QuantityERP=0` nu este tratat automat ca lipsă WME;
- pentru zonele speciale, un efect de mapare este confirmat numai când soldul WMS este egal cu soldul WME;
- diferența raportată este separată de diferența reală WMS-WME.

Cazul real DS084100102 a fost reconstruit astfel:

- Depozitare: -240;
- MOSTRE: +1 efect de mapare al raportului, cu WMS=1 și WME=1;
- total raport: -239.

Rezultat automat: `-239 = -239 explicat + 0 neexplicat`, verdict REVIEW, nivel B, status `ASTEPTARE_VALIDARE`.

## REGISTRU_CAZURI

Motorul produce un payload determinist `registry_update` pentru upsert în `CONTROL_RECONCILIERE_WMS_WME / REGISTRU_CAZURI`.

Motorul nu conține credențiale Google și nu scrie direct în Drive. Payload-ul:

- identifică rândul prin `CASE_ID`, cu fallback pe produs/perioadă/tip eveniment;
- păstrează câmpurile externe dacă motorul nu are valori noi;
- scrie numai regulile care au contribuit efectiv la explicație;
- diferențiază `IN_ANALIZA` de `ASTEPTARE_VALIDARE`;
- păstrează lista tehnică completă în JSON, iar registrul primește doar sumarul managerial.

## Validare reală

Checkpoint-ul v0.4 a fost verificat end-to-end pe:

- DS099904127;
- DS099904230;
- DS099904370;
- DS084100102.

Regresiile v0.3 au rămas neschimbate, iar cazul RECEIPT/TRANSFER v0.4 este explicat integral fără MATCH forțat.

## Criteriu de închidere v0.4

v0.4 poate fi integrat în `main` când:

- CI este verde;
- cele patru cazuri reale trec end-to-end;
- indexul rapid produce aceleași rezultate ca fluxul v0.3;
- RECEIPT, DELIVERY, TRANSFER_MOSE și documentele derivate sunt tratate conservator;
- payload-ul de registry este validat pe un caz real fără duplicarea rândului;
- documentația și versiunile engine/rules sunt sincronizate;
- RAW-urile rămân în afara GitHub.

La checkpoint-ul curent, criteriile sunt îndeplinite.
