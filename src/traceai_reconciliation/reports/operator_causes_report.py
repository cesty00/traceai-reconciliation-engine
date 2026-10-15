"""Concise operator-first CAUSES report; full forensic report remains separate.

No hardcoded product IDs or assumed evidence. Original source rows are kept in JSON.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from traceai_reconciliation.reports.report_model import CaseReport


def _table(doc, headers, rows):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Light Shading Accent 1"
    for cell, label in zip(table.rows[0].cells, headers):
        cell.text = str(label)
    for values in rows:
        cells = table.add_row().cells
        for cell, value in zip(cells, values):
            cell.text = str(value if value is not None else "Neidentificat")
    for row in table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(8)
    return table



def _date_for_operator(value):
    """Display source dates consistently; midnight is not evidence of a time."""
    from datetime import datetime
    raw = str(value or "").strip()
    if not raw or raw == "-":
        return "Neidentificată"
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return raw
    return (parsed.strftime("%d.%m.%Y %H:%M:%S")
            if parsed.time().isoformat() != "00:00:00"
            else parsed.strftime("%d.%m.%Y"))


def _source_reference(entry):
    """Only expose source identifiers explicitly carried by case evidence."""
    for key in ("source_row", "SourceRowNumber", "source_row_number", "row_number", "source_line"):
        value = entry.get(key)
        if value is not None and str(value).strip() not in ("", "-"):
            return str(value)
    return "Nedisponibil în cronologia cazului"



def _operational_status(*, confirmed_cause: bool = False,
                        operator_approved: bool = False,
                        proposed_correction: dict | None = None) -> str:
    """Fail closed: a computed quantity residual never authorizes a correction."""
    if (operator_approved and proposed_correction
            and all(proposed_correction.get(key) for key in
                    ("system", "document", "operation", "evidence"))):
        return "CORECȚIE PROPUSĂ"
    if confirmed_cause:
        return "EXPLICAT"
    return "REVIEW"


def _decision(doc, checks):
    doc.add_heading("Ce verifică operatorul", level=2)
    for check in checks:
        doc.add_paragraph("☐ " + check)
    doc.add_heading("Decizia operatorului", level=2)
    _table(doc, ["Decizie", "Observații / dovezi suplimentare"], [
        ("☐ Confirmat   ☐ Respins   ☐ Verificare suplimentară", "......................................."),
        ("Verificator / dată", "......................................."),
    ])


def generate_operator_causes_docx(
    report: CaseReport, output_path: str | Path, *,
    details: dict | None = None,
) -> Path:
    """Demo v0.2-like read-only report, with bounded, evidence-grounded pages."""
    details = details or {}
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(1.7)
    section.bottom_margin = Cm(1.6)
    section.left_margin = Cm(1.8)
    section.right_margin = Cm(1.8)
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(9)
    for name in ("Heading 1", "Heading 2"):
        doc.styles[name].font.color.rgb = RGBColor(28, 72, 106)
    doc.add_heading("RAPORT OPERATOR — CAUSES", 0)
    doc.add_paragraph(f"{report.case_id}  |  {report.report_date}  |  TraceAI Control")
    doc.add_paragraph(f"{report.product_code} — {report.product_name}")
    doc.add_paragraph(f"Perioada: {report.period}   •   Verdict: {report.verdict}   •   Status: {report.case_status}")
    doc.add_heading("Rezumat stoc — toate gestiunile", level=1)
    zone_rows = details.get("stock_report_zone_matching", {}).get("rows", [])
    rows = [
        (
            row.get("report_warehouse", "Neidentificat"),
            f'{float(row.get("quantity_wms") or 0):,.3f}',
            f'{float(row.get("quantity_erp") or 0):,.3f}',
            f'{float(row.get("report_difference") or 0):+,.3f}',
        )
        for row in zone_rows
    ]
    if not rows:
        rows = [("Gestiuni indisponibile în datele investigației", "—", "—", "—")]
    _table(doc, ["Zonă / gestiune", "WMS", "WME", "WMS − WME"], rows)
    if zone_rows:
        wms = sum(float(x.get("quantity_wms") or 0) for x in zone_rows)
        wme = sum(float(x.get("quantity_erp") or 0) for x in zone_rows)
        doc.add_paragraph(f"TOTAL ARTICOL: WMS {wms:,.3f} | WME {wme:,.3f} | Diferență {wms-wme:+,.3f} {report.unit}")
    staging = any(f.get("type") == "RECEPTION_STAGING_INCLUDED_IN_STORAGE" for f in report.findings)
    if staging:
        doc.add_paragraph("Regulă confirmată: Recepție nerelocată este zonă operațională a Depozitării; rândurile originale rămân vizibile.")
    doc.add_paragraph("Un sold egal nu dovedește reconcilierea tuturor documentelor.")
    doc.add_heading("Registru CAUSES", 1)
    events = report.operation_timeline
    deliveries = defaultdict(lambda: {"out": [], "ret": [], "ae": []})
    import re
    for entry in events:
        system = str(entry.get("system") or "").upper()
        name = str(entry.get("document") or "").upper().strip()
        operation = str(entry.get("operation_type") or "").upper()
        if system == "WMS":
            m = re.fullmatch(r"SFA(\d+)(-1)?", name)
            if m and operation in ("LIVRARE", "RECEPTIE"):
                key = "ret" if m.group(2) and operation == "RECEPTIE" else "out" if not m.group(2) and operation == "LIVRARE" else None
                if key:
                    deliveries[m.group(1)][key].append(entry)
        elif system == "WME" and operation == "AE" and name.isdigit():
            deliveries[name]["ae"].append(entry)
    flows = []
    for no, x in sorted(deliveries.items()):
        if x["out"] and x["ret"] and x["ae"]:
            net = sum(float(e.get("quantity") or 0) for e in x["out"]+x["ret"])
            erp = sum(float(e.get("quantity") or 0) for e in x["ae"])
            if abs(net-erp) <= .001:
                flows.append((no, x, net))
    pv = [x for x in report.unmatched_operations if str(x.get("operation_type") or "").upper() in ("PV", "INV-MIN", "INV-PLS")]
    # Warehouse classification comes from an exact WME F source entry,
    # never from the customer's name or a free-text reason.
    wme_f_mose_docs = {
        str(e.get("document") or "").strip().upper()
        for e in events
        if str(e.get("system") or "").upper() == "WME"
        and str(e.get("operation_type") or "").upper() == "F"
        and str(e.get("warehouse") or "").strip().upper() == "MOSE"
    }
    mose = [
        x for x in report.unmatched_operations
        if str(x.get("system") or "").upper() == "WME"
        and str(x.get("operation_type") or "").upper() == "F"
        and str(x.get("document") or "").strip().upper() in wme_f_mose_docs
    ]
    # Multiple investigative views can surface the same economic document.
    # Keep one operator row per exact system, type and document; prefer a dated row.
    def unique_documents(items):
        chosen = {}
        for item in items:
            key = (str(item.get("system") or "").upper(),
                   str(item.get("operation_type") or "").upper(),
                   str(item.get("document") or "").strip().upper())
            current = chosen.get(key)
            if current is None or (str(current.get("date") or "-") == "-"
                                   and str(item.get("date") or "-") != "-"):
                chosen[key] = item
        return list(chosen.values())

    pv = unique_documents(pv)
    mose = unique_documents(mose)
    timeline_by_document = {}
    for entry in events:
        key = (str(entry.get("system") or "").upper(),
               str(entry.get("document") or "").strip().upper(),
               str(entry.get("operation_type") or "").upper())
        timeline_by_document.setdefault(key, []).append(entry)

    def sourced_row(item):
        system = str(item.get("system") or "").upper()
        document = str(item.get("document") or "").strip().upper()
        operation = str(item.get("operation_type") or "").upper()
        matches = timeline_by_document.get((system, document, operation), [])
        # An inventory without document number cannot be attributed to a
        # timeline row solely on the basis of equal quantities.
        match = matches[0] if len(matches) == 1 and document not in ("", "-") else None
        date = (match.get("date") if match else item.get("date")) or "Neidentificată"
        if date == "-":
            date = "Neidentificată"
        quantity = (match.get("quantity") if match else item.get("quantity"))
        warehouse = match.get("warehouse") if match else "Neidentificată"
        return (_date_for_operator(date), system, document, operation, quantity, warehouse,
                _source_reference(match) if match else _source_reference(item),
                str(item.get("reason") or "-"))

    registru = []
    if staging:
        registru.append(("01", "Recepție nerelocată în Depozitare", "Clarificare operațională confirmată"))
    for no, _, _ in flows[:8]:
        registru.append((f"{len(registru)+1:02}", f"Livrare / retur {no}", "Cantități concordante; verificare documentară"))
    if pv:
        registru.append((f"{len(registru)+1:02}", "Inventare și corecții", "REVIEW"))
    if mose:
        registru.append((f"{len(registru)+1:02}", "Documente MOSE", "REVIEW"))
    if not registru:
        registru.append(("01", "Verificare documentară", "REVIEW"))
    _table(doc, ["ID", "Obiect verificare", "Stadiu"], registru)
    doc.add_paragraph("Fiecare decizie se validează separat. Raportul tehnic și cronologia completă sunt păstrate în JSON.")
    doc.add_paragraph(
        "LEGENDĂ: EXPLICAT = mecanism operațional confirmat, fără a închide articolul; "
        "REVIEW = dovadă sau corespondent încă de verificat; "
        "CORECȚIE PROPUSĂ = numai după confirmarea documentară și aprobarea operatorului. "
        "Niciun status nu autorizează modificări automate WMS/WME."
    )

    counter = 0
    def page(title):
        nonlocal counter
        counter += 1
        doc.add_page_break()
        doc.add_heading(f"CAUSE {counter:02} — {title}", 1)
        doc.add_heading("LOCALIZARE RAPIDĂ ÎN SISTEMELE REALE", 2)
    if staging:
        page("Recepție nerelocată în Depozitare")
        doc.add_paragraph("Stadiu operațional: " + _operational_status(confirmed_cause=True))
        _table(doc, ["Gestiune", "WMS", "WME", "Diferență"], rows)
        doc.add_paragraph("Perimetru operațional comun confirmat. Nu înseamnă că toate documentele sunt validate.")
        _decision(doc, ["Confirmă cantitatea rămasă în Recepție.", "Verifică relocarea fără dublare de stoc."])
    for no, match, net in flows[:8]:
        page(f"Livrare {no} și retur parțial")
        doc.add_paragraph("Stadiu operațional: " + _operational_status() + " — retur de validat documentar.")
        entries = match["out"]+match["ret"]+match["ae"]
        _table(doc, ["Sistem", "Data / ora", "Document", "Operațiune", "Cantitate", "Gestiune", "Rând sursă"], [
            (e.get("system"), _date_for_operator(e.get("date")),
             e.get("document"), e.get("operation_type"),
             e.get("quantity"), e.get("warehouse"), _source_reference(e)) for e in entries
        ])
        metadata_entries = [e for e in match["ret"] if e.get("source_metadata")]
        if metadata_entries:
            doc.add_paragraph("Identificatori expliciți din exportul WMS (retur):")
            _table(doc, ["Document", "Rând sursă", "NIR", "Palet", "Lot", "Locație"], [
                (e.get("document"), _source_reference(e),
                 e["source_metadata"].get("nir", "Nedisponibil"),
                 e["source_metadata"].get("pallet", "Nedisponibil"),
                 e["source_metadata"].get("lot", "Nedisponibil"),
                 e["source_metadata"].get("location", "Nedisponibil"))
                for e in metadata_entries
            ])
        erp = sum(float(e.get("quantity") or 0) for e in match["ae"])
        doc.add_paragraph(f"Calcul: WMS net {net:,.3f} / WME AE {erp:,.3f} / Rezidual {net-erp:+,.3f} {report.unit}.")
        doc.add_paragraph("Egalitatea documentară cantitativă nu confirmă singură că recepția este un retur real.")
        _decision(doc, ["Confirmă returul în documentul de recepție/NIR.", "Verifică produsul, gestiunea, lotul și referințele sursă."])
    for title, items, checks in [
        ("Inventare și corecții",pv,["Găsește PV-ul și ajustarea WMS.", "Verifică data, cantitatea, semnul, lotul și gestiunea."]),
        ("Documente F în MOSE",mose,["Verifică factura F și clientul înscris pe factură.", "Caută NT WME de intrare în gestiunea MOSE și livrarea WMS TRANSFER_MOSE corespunzătoare.", "Nu confunda gestiunea MOSE cu clientul MOSE Business Distribution."]),
    ]:
        if not items:
            continue
        page(title)
        doc.add_paragraph("Stadiu operațional: " + _operational_status())
        _table(doc, ["Data/ora sursă", "Sistem", "Document", "Operațiune", "Cantitate mișcare", "Gestiune", "Rând sursă", "Motiv / efect tehnic"], [
            sourced_row(x) for x in items[:15]
        ])
        doc.add_paragraph(
            "Cantitate mișcare = semnul din cronologia sursă când există corespondență exactă. "
            "Efectul tehnic asupra diferenței, dacă apare în motiv, este alt indicator și "
            "nu trebuie confundat cu semnul mișcării."
        )
        if title == "Documente F în MOSE":
            doc.add_paragraph(
                "REGULĂ MOSE CONFIRMATĂ: gestiunea MOSE este internă. "
                "Marfa iese din Depozit Principal prin Livrare WMS TRANSFER_MOSE "
                "și intră în MOSE prin NT WME. Factura F este o ieșire ulterioară "
                "din gestiunea MOSE către clientul înscris pe document; "
                "nu reprezintă transferul în sine. "
                "MOSE Business Distribution este un client separat, nu gestiunea MOSE."
            )
            transfer_info = details.get("transfer_mose_matching") or {}
            matched = transfer_info.get("matches")
            if matched is not None:
                doc.add_paragraph(
                    f"Transferuri interne WMS ↔ NT WME identificate de motor: {matched}. "
                    "Această asociere nu validează automat facturile F."
                )
        doc.add_paragraph("REVIEW: documentele nu sunt considerate cauze confirmate.")
        _decision(doc, checks)
    doc.add_paragraph("NOTĂ: raportul nu autorizează ajustări WMS/WME. Ora 00:00 din WME poate însemna doar dată calendaristică.")
    doc.save(target)
    return target
