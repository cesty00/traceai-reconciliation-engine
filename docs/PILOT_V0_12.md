# v0.12 Controlled Pilot

Scopul pilotului este validarea operațională a candidatului `v0.12.0` pe date reale, fără a modifica WMS sau WME.

## Condiții înainte de rulare

- commit-ul candidat trebuie să aibă `pytest`, `daily-release-gate`, `release-readiness-gate` și `release-candidate-gate` verzi;
- profilul DAILY trebuie să conțină `snapshot_at` real;
- sursele RAW trebuie să fie complete pentru cutoff-ul declarat;
- nu se activează nicio mutație WMS/WME;
- nu se aplică automat registry updates;
- operatorul păstrează decizia finală.

## Rulare

Se rulează fluxul DAILY normal pe un set controlat de produse/cazuri reale.

După finalizarea rulării, se validează sumarul:

```bash
traceai-pilot-acceptance /cale/catre/daily_run_summary.json
```

Comanda întoarce exit code `0` numai dacă pilotul respectă contractul minim de acceptanță.

## Criterii de acceptanță automate

Validatorul cere:

- status `SUCCESS` sau `SUCCESS_WITH_REVIEW`;
- zero erori de run;
- semnătură prezentă;
- hash-uri pentru toate cele șase surse obligatorii;
- manifest de run valid;
- authority boundary fail-closed;
- `snapshot_at` explicit;
- `daily_case_summary.json` pentru fiecare caz activ;
- contract valid pentru fiecare daily case summary;
- Run Store prezent și sincronizat cu run-ul;
- aceeași versiune engine în Run Store și în executabil;
- `snapshot_at` persistat în Run Store.

## Validare umană obligatorie

Un rezultat automat `accepted=true` nu înseamnă aprobare contabilă sau operațională. Înainte de release intern stabil trebuie verificate manual cel puțin:

- că explicațiile cauzelor sunt utile operatorului;
- că recomandarea indică sistemul/documentul corect de verificat;
- că nu există forced MATCH;
- că diferențele neexplicate rămân REVIEW;
- că niciun fișier RAW nu a fost modificat;
- că nu s-au produs mutații automate WMS/WME.

## Rezultat

Dacă validatorul automat este verde și validarea umană este aprobată, candidatul poate fi promovat la release intern stabil `v0.12.0`.
