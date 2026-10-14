# G1 — Contract de date WMS ↔ WME (draft, verificare implementare)
Data: 2026-10-14. Scope: V1 Daily. Statut: IN REVIEW, nu este o implementare completă a provenienței.

## Bază verificată în cod
- `source_readers.py`: `ALIASES`, `resolve_column`, `parse_operational_dates`, `WME_STANDARD_COLUMNS`, `read_wme_product`.
- `source_index.py`: `SQLiteSourceIndex`, fingerprint `file_name/size/sha256`, tabele `wms`, `wme`, `production`, indexare pe cod WMS și denumire WME.
- `delta_movement_window.py`: limite strict `(start_exclusive, end_inclusive]`; date nevalide blochează fereastra; rezultatele sunt dicționare fără ID de rând original garantat.
- Metodologie: manual de reconciliere v6 (Google Drive ID 1wMKcj7KbGhpGyO3M1Ve2rqMsH3j57Dsp).

## WMS — contract minim pentru fiecare eveniment
- Identitate produs: `Cod articol`; denumire și UM pentru verificări secundare.
- Dată și tip eveniment: `Data`, `Tip operatiune` (normalizare contextuală).
- Document: `Numar comanda`, `Document intrare`, referință/partener când există.
- Cantitate cu semn explicit și unitate.
- Mișcări între gestiuni: `Locatie sursa`, `Locatie destinatie`, eventual `Depozit`; absența sensului => REVIEW.
- Identitatea sursei: hash SHA256 + index fizic original al rândului + valoarea brută a câmpurilor.

## WME — contract minim
- `LineNo`, `OperationType`, `Document`, `Date`, `Incoming`, `Outgoing`, `SignedQuantity=Incoming-Outgoing`.
- `ProductName`, `WMEItemId`, `Warehouse`, `CounterWarehouse`, `Partner`, `Unit`, `Note`, `InternalRef`.
- `LineNo` singur nu este dovedit identificator unic pentru toate exporturile. Identitatea rândului trebuie să includă hash sursă + coordonată fizică + identificatori documentari.
- Pentru NT: ambele sensuri trebuie verificate, fără dublarea intrărilor; la transferurile WMS între locații fără echivalent NT, nu inventăm documente.

## Snapshot stoc
- Cod produs, gestiune/zonă din raport, sold WMS, sold WME, diferență și timestamp exact al exportului.
- Nu deducem scope AGGREGATE din totaluri egale. Lista gestiunilor WMS și WME, versiunea mapării și proveniența constituie precondiții pentru calculul cauzal la nivel agregat.
- Dacă între două snapshoturi scope-ul sau cutoff-ul nu este comparabil => REVIEW.

## Lacune confirmate, de tratat înainte de G1 DONE
1. Indexarea WMS cu `to_sql(index=False)` nu salvează explicit numărul original de rând al CSV; `read_wms_product` face `SELECT *`, fără ordonare cu identitate fizică garantată.
2. Cititorul WME extrage `LineNo`, dar nu păstrează în `WME_STANDARD_COLUMNS` coordonata de rând XLSX/sheet; indexul SQLite omite proveniența la nivel de rând.
3. `build_delta_movement_window` transmite dicționare fără cheie canonică `source_row_id`; nu putem verifica automat că un rând dintr-un raport este exact cel din exportul original.
4. Selecția WME după `ProductName` trebuie verificată contra unui mapping confirmat `WMEItemId` ↔ `Cod articol` WMS; denumirile nu sunt chei fiabile universal.
5. Lipsesc un contract formal de respingere pentru date lipsă/ambigue și metadate complete pentru perimetrul gestiunilor.
6. Nu avem încă test end-to-end care verifică citire raw → index cu ID rând → eveniment → verdict → raport DOCX.

## Criterii de acceptare G1
- [ ] Fiecare rând WMS și WME are ID stabil derivat din hash-ul sursei + coordonata fizică, fără schimbarea cantității originale.
- [ ] Exportul păstrează valorile brute, valorile normalizate și avertismentele de parsare.
- [ ] Evenimente fără cod/articol, dată, cantitate, semn sau document obligatoriu devin REVIEW/INPUT_INVALID, nu MATCH.
- [ ] Două surse cu denumire similară dar WMEItemId diferit nu se unesc fără mapare.
- [ ] Teste pozitive/negative pe exporturi reale, inclusiv NT, BC, PV și mutări interne.
- [ ] CI complet SUCCESS la commitul exact; evaluare umană a rapoartelor; fără corecții automate.

## Ordine recomandată
G1.1: introduceți ID rând în cititoarele și indexul surselor, fără schimbare de logică MATCH.
G1.2: testați fidelitatea importului (semn, UM, date, document, ID articol).
G1.3: contractul de identificare între cod produs WMS și WMEItemId; ambiguități blocate.
G1.4: integrarea câmpurilor de proveniență în analiza Daily și raport, apoi gate G1.
