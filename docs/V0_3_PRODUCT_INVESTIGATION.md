# v0.3 — Investigație reală pe produs

## Obiectiv

v0.3 leagă sursele reale ale unei verificări de produs de obiectul `CaseReport` și de generatorul DOCX introdus în v0.2.

Fluxul executabil este:

`raport stoc → produs → stoc inițial WMS → mișcări WMS → fișă WME → producție → matching operațional → rezultat investigație → CaseReport → JSON + DOCX`

## Principii de implementare

- RAW-urile rămân nemodificate și nu sunt versionate în GitHub.
- Fișierele CSV mari sunt citite în chunk-uri și filtrate cât mai devreme pe produs.
- XLSX-urile mari sunt citite read-only atunci când este necesar.
- Maparea WMS ↔ WME trebuie să fie demonstrabilă; lipsa sau ambiguitatea păstrează cazul în REVIEW.
- Motorul nu inventează cauze și nu forțează MATCH.
- Diferența de deschidere este separată de diferența generată în perioada analizată.
- Componentele explicative se aplică după forța dovezii; o regulă generică nu poate bloca o corelare mai puternică.
- Mișcările WME non-standard fără legătură documentară sunt raportate ca dovezi reziduale, dar nu explică automat diferența.
- JSON-ul tehnic și DOCX-ul sunt generate din același rezultat de investigație.

## Matching operațional implementat

v0.3 include:

- WMS `PRODUCTION-OUT` ↔ WME `NP`, pe document normalizat și cantitate;
- identificarea perechilor WMS de reversare producție;
- WMS `PRODUCTION-IN` ↔ WME `BC`;
- netarea `Livrare + Receptie/retur` WMS înainte de comparația cu WME `AE`;
- flux candidat `INS.DET ↔ DETERIORATE`, numai când transferul, NT-ul WME și corecția WMS se închid cantitativ;
- detector conservator pentru `COR STOC` WMS fără document, după excluderea fluxurilor mai puternic clasificate;
- detector pentru mișcări WME non-standard, doar ca evidență reziduală până la validarea unei punți documentare.

## Intrări CLI v0.3

Pentru investigația completă sunt necesare:

- `--product`
- `--case-id`
- `--period`
- `--stock-report`
- `--opening-stock-wms`
- `--wms-movements`
- `--wme-ledger`
- `--production`
- `--nomenclature`
- `--output-docx`

Opțional:

- `--output-json`
- `--report-date`
- `--engine-commit-sha`
- `--rules-version`

## Validare reală

Checkpoint-ul v0.3 a fost validat end-to-end pe trei produse reale independente, fără versionarea datelor comerciale în repository.

Pentru fiecare caz s-a verificat:

1. reconstrucția soldului inițial;
2. reconstrucția mișcării nete WMS;
3. reconstrucția mișcării nete WME;
4. separarea diferenței de deschidere de diferența perioadei;
5. matching-ul documentar disponibil;
6. operațiunile rămase fără corespondent;
7. consistența `diferență inițială = diferență explicată + diferență neexplicată`;
8. generarea automată a JSON-ului tehnic și a DOCX-ului.

Cele trei tipare de regresie sunt păstrate în teste sintetice/scrubbed, fără RAW real.

## Criteriu de închidere v0.3

v0.3 este considerat finalizat atunci când:

- testele unitare și de regresie sunt verzi;
- trei cazuri reale independente trec end-to-end;
- rezultatul automat reproduce reconstrucția validată;
- diferențele fără dovadă suficientă rămân REVIEW;
- RAW-urile nu sunt modificate și nu ajung în GitHub;
- DOCX și JSON sunt generate automat din aceeași execuție.

Aceste criterii sunt îndeplinite la checkpoint-ul curent.

## Următorul strat

v0.4 este etapa de stabilizare și extindere: recepții, retururi și lanțuri speciale suplimentare, integrarea registrului de cazuri, performanță/cache și validare pe un eșantion mai mare de produse.
