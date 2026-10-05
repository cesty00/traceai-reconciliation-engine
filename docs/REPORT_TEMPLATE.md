# Șablon oficial raport verificare produs WMS ↔ WME

Versiune: 1.0

Fiecare verificare de produs trebuie să genereze un raport DOCX. Raportul este o ieșire obligatorie a motorului și trebuie să fie reproductibil din rezultatul tehnic structurat al cazului.

## Principii

- Un raport = un produs / un CASE_ID.
- Verdictul este separat de cauză.
- O diferență reziduală nu este automat o eroare reală.
- Nu se forțează MATCH.
- Cauza trebuie încadrată ca confirmată, probabilă sau nedeterminată.
- Recomandările nu autorizează automat ajustări WMS/WME sau regularizări contabile.
- Fiecare concluzie trebuie să fie trasabilă: sursă brută → cheie de legătură → regulă → nivel de probă → verdict → cauză.
- Datele RAW rămân în Google Drive, nu în GitHub.

## Structura raportului

1. Rezumat executiv
2. Obiectul și limitele verificării
3. Situația de pornire
4. Surse și dovezi verificate
5. Metoda de verificare aplicată
6. Rezultatul reconcilierii
7. Constatări
8. Analiza cauzei
9. Impactul constatat
10. Recomandări de rezolvare
11. Verdict și închidere caz
12. Validare umană

### Anexe

- Anexa A — Jurnal cronologic al operațiunilor relevante
- Anexa B — Operațiuni fără corespondent / diferențe punctuale
- Anexa C — Trasabilitatea concluziei
- Anexa D — Parametri tehnici ai execuției

## Tipuri recomandări

- P1 IMEDIATĂ — acțiune necesară pentru cazul curent
- P2 CORECTIVĂ — remedierea cauzei operaționale / de sistem
- P3 PREVENTIVĂ — prevenirea recurenței
- P4 AUTOMATIZARE / CONTROL — regulă, alertă sau control automat

## Verdicturi

- MATCH_DIRECT
- MATCH_NORMALIZARE
- MATCH_DUPA_NETARE
- REVIEW
- NOT_MATCH

## Nivel de probă

- A — confirmare directă
- B — corelare puternică
- C — probabil
- D — insuficient

## Regula de închidere

Un caz poate fi închis numai dacă raportul conține:
- diferența inițială;
- diferența explicată;
- diferența rămasă;
- cauza și nivelul de probă;
- sursele consultate;
- regula aplicată;
- recomandarea;
- statusul final;
- trasabilitatea concluziei.

Raportul trebuie să poată fi regenerat din aceleași surse, aceeași versiune de cod și aceeași versiune a regulilor.
