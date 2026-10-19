# GOV-002G — Evidence and acceptance specification
Date: 2026-10-19. Status: PARTIAL; NO GO for branch separation.

## Verified directly from GitHub source
1. tests/test_mose_source_index.py contains **one** test: only checks dedicated sqlite filename and missing cache returns false. No creation, reuse, invalidation, provenance or WME XLSX parsing test here.
2. tests/test_mose_dossier_from_index.py contains **one** test: missing raw files return SOURCE_FILES_MISSING and REVIEW. No positive full-source dossier coverage in this test file.
3. tests/test_mose_transfer_from_index.py contains **two** tests on hand-created SQLite tables. Checks quantity equality/REVIEW and unsupported NT warehouse sign REVIEW. It does not exercise the actual inherited MOSE SQLite index builder.
4. tests/test_economic_event_ledger.py contains **six** ledger unit tests for repeated source ownership, event IDs, zero-review impact and valid source coordinates. It does NOT invoke CORE engine and cannot certify global economic ownership.
5. Prior code inspection: engine.py, daily.py, self_service.py, case_builder.py have no EventOwnershipLedger or EconomicEvent references. A **complete repository-wide search was not available through the current connector**. Therefore general non-usage remains unproven, although principal entrypoints examined do not invoke it.

## Unacceptable assumptions
- CI success on combined branch != isolated CORE/MOSE tests.
- Filename `test_mose_source_index.py` != actual index-build acceptance.
- Two equal quantities in hand-constructed sqlite != documentary transfer equivalence.
- Ledger unit tests != global protection from double accounting.

## Required tests before PR split (all currently PENDING)
| ID | Scenario | Required assertions |
|---|---|---|
| GOV-AT-01 | Minimal synthetic WMS CSV+WME XLSX built through MOSESQLiteSourceIndex | source files unchanged; correct physical row coordinate; metadata SHA; index built |
| GOV-AT-02 | Reuse unchanged two-source index | no rebuild; same source identities; no false reliance on production argument |
| GOV-AT-03 | Modify one WME document quantity | source hash changes; invalidate/rebuild index; preserved exact provenance |
| GOV-AT-04 | WMS or WME malformed/missing mandatory columns | safe error; no false successful index or case |
| GOV-AT-05 | Duplicate economic source row claimed by two different CORE matcher paths | no duplicate confirmed delta; ambiguity REVIEW/blocked; causality and totals preserved |
| GOV-AT-06 | One source row offered as REVIEW evidence in one matcher, CONFIRMED in another | review has zero economic impact; confirmed contribution once only |
| GOV-AT-07 | MOSE WMS transfer DP→MOSE and WME NT split by products | signed three-leg control; document identity stays unverified without evidence |
| GOV-AT-08 | Operator case on full authorized sources → DOCX | original row IDs, source hashes, delta trace, clear unresolved checks; human approval |
| GOV-AT-09 | CORE-only extracted branch | unit/integration suite, UI and report tests, no MOSE or EXT hidden import needed |

## Architectural verdict
**GOV-002 remains OPEN.** First complete global reference scan and test coverage review, then implement acceptance tests on a dedicated test-only branch after explicit approval. Do not cherry-pick or merge PR #56.
