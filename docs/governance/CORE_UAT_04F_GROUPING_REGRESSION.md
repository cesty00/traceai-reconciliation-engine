# CORE-UAT-04F — Isolated inventory grouping regression
Date: 2026-10-21
Status: SYNTHETIC / CORE UNCHANGED

Added independent grouping sidecar preserving Document and Lot per original WMS event, grouped by existing (_day,_reason) semantics. Source pointer is explicitly UNVERIFIED, not fabricated. Tests compare unchanged actual match_inventory_adjustments() before and after using sidecar and assert -86.35 sample net, three distinct rows, document multiplicity and fail-closed missing lot. These tests do not validate source provenance nor GOV-AT-05/06 global event ownership. Real CORE integration still requires approved change, versioned backward-compatible extension and audit of source pointer binding. PR #67 Draft, GOV-002 OPEN, V1 NO_GO.
