# Daily Operator View — v0.10 design

## Obiectiv

Daily use trebuie sa raspunda rapid la intrebarea operatorului:

**De unde vine diferenta si ce trebuie verificat/corectat operational?**

Motorul continua sa faca investigatia tehnica completa in spate. Operatorul primeste un
rezultat compact si actionabil.

## Contract rezultat

Pentru fiecare articol:

- articol / denumire / UM;
- diferenta WMS-WME;
- cauza determinata de motor;
- nivelul dovezii;
- regulile care explica diferenta;
- sistemul sau zona de verificat;
- actiunea recomandata operatorului;
- rezidualul ramas;
- dovezile relevante;
- blockers si warnings;
- status operator: CONFIRMAT sau REVIEW.

## Tinte operationale

- `REPORT_MAPPING`: diferenta este de scope/mapare; nu se modifica stocul.
- `OPENING_BALANCE`: se reconciliaza soldul initial WMS versus WME.
- `WMS_WME_DOCUMENT_FLOW`: se verifica documentul operational BC/NP/transfer.
- `STOCK_ADJUSTMENT`: se verifica ajustarea/correctia de stoc.
- `REVIEW`: dovezile nu sunt suficiente pentru recomandare operationala sigura.

## Regula de autoritate

Daily Operator View este read-only.

Motorul:
- nu opereaza automat WMS;
- nu opereaza automat WME;
- nu transforma o explicatie in ajustare de stoc;
- nu forteaza MATCH;
- nu recomanda corectie de stoc pentru diferente de raport/mapare.

Operatorul confirma documentul sursa, face corectia in sistemul corect si apoi ruleaza
din nou verificarea.

## Exemplu

Pentru o diferenta de +5 KG explicata prin MOSTRE:

- cauza: mapare/scope gestiune speciala;
- reguli: GST-02/GST-03;
- tinta: REPORT_MAPPING;
- actiune: nu modifica WMS/WME; corecteaza/verifica maparea raportului;
- rezidual: 0;
- status: CONFIRMAT.

Acest contract este implementat in
`src/traceai_reconciliation/investigation/daily_operator.py`.
