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
