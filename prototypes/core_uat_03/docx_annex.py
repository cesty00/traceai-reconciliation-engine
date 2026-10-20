"""CORE-UAT-03B standalone synthetic DOCX annex preview, not production-wired.

This creates a separate file, never edits the original case DOCX.
Only validated/identified statuses already present in a display payload are presented;
a human statement never changes the economic verdict.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
from docx import Document


def render_validation_annex(display: Mapping[str, Any], output_path: str | Path) -> Path:
    required = ("case_id", "product_code", "difference", "residual",
                "attribution_status", "justification_status",
                "economic_verdict_unchanged", "automatic_evidence")
    missing = [key for key in required if key not in display]
    if missing:
        raise ValueError("missing display fields: " + ", ".join(missing))
    if display["attribution_status"] not in ("CAUSE_IDENTIFIED", "REVIEW"):
        raise ValueError("unsupported attribution status")
    if display["justification_status"] not in ("OPERATIONAL_REVIEW", "OPERATOR_VALIDATED"):
        raise ValueError("unsupported justification status")
    for key in ("automatic_approval_allowed", "registry_apply_allowed",
                "wms_mutation_allowed", "wme_mutation_allowed"):
        if display.get(key) is not False:
            raise ValueError("unsafe or missing authority: " + key)
    if display["justification_status"] == "OPERATOR_VALIDATED":
        statement = display.get("operator_statement")
        if not isinstance(statement, dict) or not all(
            str(statement.get(key) or "").strip() for key in
            ("reason_code", "comment", "supporting_document",
             "reviewer", "validated_at", "scope")
        ):
            raise ValueError("incomplete operator validation")

    target = Path(output_path)
    if target.exists():
        raise FileExistsError("refusing to overwrite any existing report")
    if target.suffix.lower() != ".docx":
        raise ValueError("DOCX output expected")

    doc = Document()
    doc.add_heading("Anexa separata - diagnostic si justificare", 0)
    doc.add_paragraph("PROTOTIP SINTETIC. Nu constituie autorizare de ajustare WMS/WME.")
    doc.add_heading("Identificare", 1)
    doc.add_paragraph(f"Caz: {display['case_id']} | Articol: {display['product_code']}")
    doc.add_paragraph(f"Diferenta raportata: {display['difference']} | Rezidual: {display['residual']}")
    doc.add_heading("Constatare automata", 1)
    doc.add_paragraph(f"Atribuire documentara: {display['attribution_status']}")
    for item in display["automatic_evidence"]:
        if isinstance(item, dict):
            doc.add_paragraph(
                f"Document {item.get('document_ref', 'NECUNOSCUT')}; "
                f"rand sursa {item.get('physical_row', 'NECUNOSCUT')}; "
                f"hash {item.get('source_hash', 'NECUNOSCUT')}"
            )
    doc.add_heading("Declaratia operatorului", 1)
    doc.add_paragraph(f"Status justificare: {display['justification_status']}")
    statement = display.get("operator_statement")
    if isinstance(statement, dict):
        for key in ("reason_code", "comment", "supporting_document",
                    "reviewer", "validated_at", "scope"):
            doc.add_paragraph(f"{key}: {statement.get(key) or 'NECOMPLETAT'}")
    doc.add_heading("Verdict economic - neschimbat", 1)
    doc.add_paragraph(str(display["economic_verdict_unchanged"]))
    doc.add_paragraph("Confirmarea justificarii NU confirma MATCH economic si NU autorizeaza ajustarea stocului.")
    target.parent.mkdir(parents=True, exist_ok=True)
    doc.save(target)
    return target
