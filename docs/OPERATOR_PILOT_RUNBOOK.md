# Operator pilot — start and limits

Install from the branch checkout:
```bash
python -m pip install -e ".[ui,dev]"
streamlit run operator_app.py
```

The pilot interface uses the existing `run_self_service_case` engine without changing the matchers. Workflow: upload six source files, inspect all products including zero difference, select product, start investigation, download DOCX and JSON evidence.

## Safety
- This pilot is read-only with respect to WMS/WME; it stores uploaded sources locally in a temporary session directory, and does not push them to GitHub or Drive.
- The Streamlit server host must be access-restricted and storage policy approved before use with company data. A temporary directory is **not** a secure retention/deletion policy.
- All six source types and an explicit investigation period are mandatory before running a case; source readiness performs the engine validation.
- The stock view derives difference as WMS − ERP and displays `Concordanta_cu_raportul` whenever the source provides `QuantityDifference`. A false value is a source-report conflict requiring review.
- A zero stock difference does not certify corresponding movements.
- Reports may remain REVIEW/HOLD. Operator validates all physical movements and changes manually.
- App is a **pilot implementation** and has not yet passed full original-source E2E / operator UAT.

## Important next tests
1. Use original official stock report and six source exports and validate parser, column naming and period.
2. Verify performance and memory for large raw files, particularly 100MB+ uploads.
3. Validate exact report paths, output artifacts and error messages.
4. Measure time until operator receives first actionable case, compare with manual effort.
5. Check Streamlit access control, upload size, session isolation and data deletion before pilot.
