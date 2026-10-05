# v0.5 — Batch orchestration

## Obiectiv

v0.5 rulează motorul v0.4 în loturi controlate peste backlog-ul de cazuri, fără a schimba regulile de reconciliere deja validate.

Fluxul țintă:

`manifest cazuri → index surse → investigație per caz → JSON/DOCX/registry payload → batch summary → validare → aplicare registry`

## Principii

- un caz eșuat nu oprește întregul lot;
- fiecare caz are director de output separat;
- indexul operațional v0.4 se construiește/reutilizează o singură dată pe lot;
- fiecare rezultat păstrează aceeași matematică și aceleași reguli ca rularea single-case;
- batch-ul nu scrie automat în Google Drive;
- payload-urile de registry se generează per caz și se aplică numai după validarea lotului;
- resume/retry trebuie să fie determinist;
- RAW-urile rămân read-only și în afara GitHub;
- MATCH nu este forțat pentru a crește rata de închidere.

## Manifest de intrare

Manifestul batch trebuie să conțină cel puțin:

- `case_id`
- `product_code`
- `period`
- opțional `report_date`
- opțional `enabled`

Cazurile dezactivate sunt raportate ca SKIPPED.

## Output per caz

Pentru fiecare caz executat:

- `case.json` — payload tehnic complet;
- `case.docx` — raport managerial/audit;
- `registry_update.json` — payload deterministic pentru REGISTRU_CAZURI;
- status batch: `SUCCESS`, `REVIEW` sau `ERROR`.

## Batch summary

Lotul produce un `batch_summary.json` cu:

- batch_id;
- perioada/rules/engine;
- total cazuri;
- executate;
- skipped;
- success;
- review;
- error;
- timp total;
- rezultat per caz;
- mesaje de eroare;
- căile output-urilor;
- sursele și hash-urile folosite.

## Resume/retry

La reluare:

- un caz cu rezultate complete și aceeași semnătură de input poate fi SKIPPED_REUSED;
- un caz ERROR poate fi rerulat individual;
- schimbarea engine/rules/surselor invalidează reutilizarea automată;
- batch summary păstrează istoricul execuției curente, nu suprascrie dovezile vechi fără urmă.

## Acceptanță v0.5 — checkpoint 1

Înainte de rularea backlog-ului complet:

1. CI verde;
2. lot pilot de minimum 5 cazuri;
3. cel puțin un caz cu rezultat REVIEW;
4. un caz sintetic ERROR care nu oprește restul lotului;
5. rezultatele cazurilor etalon sunt identice cu rularea single-case;
6. indexul este reutilizat, nu reconstruit per caz;
7. registry payload-urile sunt generate, dar nu aplicate automat;
8. rerularea lotului poate reutiliza rezultatele complete valide.

## Etapa următoare

După validarea lotului pilot se poate trece la procesarea controlată a backlog-ului real din REGISTRU_CAZURI, în tranșe și cu checkpoint după fiecare tranșă.


## Checkpoint pilot real — 2026-10-05

Lotul pilot a fost rulat pe artifactul exact trecut prin CI, cu sursele RAW oficiale verificate față de Google Drive și cu indexul operațional v0.4 reutilizat.

### Manifest pilot

6 intrări:

- CASE-2026-000006 / DS099904127;
- CASE-2026-000010 / DS099904230;
- CASE-2026-000008 / DS099904370;
- CASE-2026-000017 / DS084100102;
- CASE-2026-000016 / DS099904015 — caz real nou din backlog;
- CASE-BATCH-ERROR-001 / DS_DOES_NOT_EXIST — caz sintetic pentru izolarea erorilor.

### Prima execuție

Rezultat batch:

- total: 6;
- executate: 6;
- REVIEW: 5;
- ERROR: 1;
- procesul batch a continuat după eroarea sintetică;
- timp total: aproximativ 11,5 secunde cu index reutilizat.

Cazurile etalon au păstrat exact rezultatele single-case:

- DS099904127: -1419 = -1402 explicat + -17 neexplicat;
- DS099904230: -617 = -608 explicat + -9 neexplicat;
- DS099904370: -935 = -934,5 explicat + -0,5 neexplicat;
- DS084100102: -239 = -239 explicat + 0 neexplicat.

Cazul nou DS099904015 a rulat fără eroare și a rămas REVIEW:

- diferență totală: -390,4;
- explicat: -34,4;
- neexplicat: -356.

Cazul sintetic invalid a produs ERROR izolat, fără oprirea lotului.

### Resume/retry

Rerularea aceluiași manifest cu aceeași semnătură de surse/engine/rules a produs:

- 5 cazuri complete → SKIPPED_REUSED;
- 1 caz ERROR → rerulat;
- executate efectiv: 1;
- reused: 5;
- timp total: aproximativ 0,29 secunde.

Nu s-au aplicat automat payload-urile REGISTRU_CAZURI în Google Drive.

### Verdict checkpoint 1

Criteriile de acceptanță pentru infrastructura batch sunt îndeplinite:

- izolare eroare per caz;
- rezultate single-case păstrate;
- index reutilizat;
- output JSON/DOCX/registry per caz;
- batch summary;
- resume/retry determinist;
- fără update automat în Drive.

Următorul pas este selecția automată a backlog-ului în loturi controlate din REGISTRU_CAZURI.
