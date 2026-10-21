# CORE INV-01 — Human document link prototype
Date: 2026-10-21
Status: ISOLATED NON-PERSISTENT PROTOTYPE / NOT OPERATIONAL UI

A standalone function stages reviewer decisions about historical WME PV to WMS inventory document association. It requires candidate documents, evidence scope, reviewer, timestamp, reason, checked personnel roles/references, documents and stock scope. A CONFIRMED documentary link needs an explicit verification flag but NEVER promotes economic MATCH or posting authority. An audit hash chain is returned as a **proposal** only; no database persistence, authorization, concurrent-update protection or verified identity integration exists. User confirmation in conversation is not application validation.

Five synthetic tests added; no source evidence or personal information committed. PR #68 remains draft. Implementation in actual UI and append-only authenticated audit store needs a distinct acceptance decision and source-backed test. GOV-002/GOV-AT-05/06 OPEN, V1 NO_GO.
