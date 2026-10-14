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

## Local PC folder mode (preferred)
1. On a Windows PC with Python 3.11+, clone/check out the PR #55 branch.
2. Run `python -m pip install -e ".[ui,dev]"` then `python -m streamlit run operator_app.py --server.address 127.0.0.1`.
3. Save official exports together in a local folder, e.g. `C:\\TraceAI\\Import\\2026-10-22`.
4. Paste that **local folder path** into Streamlit. The app proposes files based on their names, then the operator confirms or changes the six mappings. Never trust a filename as proof of correct content.
5. Check the article table (including zero-difference articles), choose one, click `Reconciliază articolul`.
6. Review evidence and save the case DOCX/JSON. Manual stock corrections remain outside TraceAI.

**Pilot constraints:** Streamlit runs on the **same PC** as the source folder. A remote-hosted Streamlit instance cannot read a local Windows folder using a typed path. Before processing sensitive data, restrict server address to 127.0.0.1, check antivirus, local permissions and approved data storage. Automatic mapping is by filename pattern with manual confirmation; content/format validation is the separate source-readiness step. Avoid claiming semantic auto-detection based solely on filenames. Large files need original-source end-to-end performance testing.
