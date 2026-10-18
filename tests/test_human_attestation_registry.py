from traceai_reconciliation.investigation.human_evidence import HumanAttestation, applicable_attestations


def _confirmation():
    return HumanAttestation(
        evidence_id="HUM-DS099902505-273779",
        product_code="DS099902505",
        system="WMS",
        source_row=273779,
        source_date="2026-09-18",
        signed_quantity=-10.0,
        unit="BUCATA",
        physical_count_confirmed=True,
        counterpart_wme_exists=False,
        statement="Verificare fizica; ajustare efectuata doar in WMS.",
        provenance="Declaratie explicita a responsabilului de verificare",
    )


def test_attestation_only_applies_to_exact_original_row():
    entry = {"system": "WMS", "source_row": 273779,
             "date": "2026-09-18 17:12:03", "quantity": -10.0,
             "operation_type": "Ajustare negativa"}
    result = applicable_attestations("DS099902505", [entry], [_confirmation()])
    assert len(result) == 1
    assert result[0]["validation_status"] == "HUMAN_CONFIRMED"
    assert result[0]["physical_count_confirmed"] is True
    assert result[0]["counterpart_wme_exists"] is False
    assert applicable_attestations("ALT_PRODUS", [entry], [_confirmation()]) == []
    assert applicable_attestations("DS099902505", [{**entry, "quantity": -11}], [_confirmation()]) == []
    assert applicable_attestations("DS099902505", [{**entry, "source_row": 999}], [_confirmation()]) == []
    assert applicable_attestations("DS099902505", [entry, entry], [_confirmation()]) == []


def test_attestation_does_not_change_matching_or_verdict():
    entry = {"system": "WMS", "source_row": 273779,
             "date": "2026-09-18 17:12:03", "quantity": -10.0}
    initial = dict(entry)
    result = applicable_attestations("DS099902505", [entry], [_confirmation()])
    assert result
    assert entry == initial
    assert "verdict" not in result[0]
