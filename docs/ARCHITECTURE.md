# Arhitectură v0.1

## Principiu

Motorul nu încearcă să obțină un procent mare de MATCH prin reguli permisive. Obiectivul este reducerea cazurilor cu cauză necunoscută.

## Flux

1. Load RAW WMS / WME / master data / producție.
2. Validează schema surselor.
3. Normalizează cheile și tipurile de operațiuni.
4. Construiește evenimente canonice.
5. Aplică întâi regulile puternice.
6. Aplică netări numai unde regula este validată.
7. Păstrează cazurile neexplicate în REVIEW.
8. NOT_MATCH este folosit numai după epuizarea regulilor validate.
9. Fiecare verdict păstrează sursa, regula, nivelul de probă și cauza.

## Primul flux implementat

Audit pe un singur produs, pornind din raportul de stoc. Următoarea etapă va adăuga reconstrucția cronologică din WMS, WME și producție.
