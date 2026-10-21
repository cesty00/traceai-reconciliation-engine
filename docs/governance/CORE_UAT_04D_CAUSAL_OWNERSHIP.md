# CORE-UAT-04D — Causal evidence ownership contract
Date: 2026-10-21
Status: isolated acceptance prototype; no CORE runtime integration.

- Event identity: system + raw file SHA-256 + original physical row + event key; document number is metadata, NOT globally unique event identity.
- Each claimed event belongs to exactly one causal component; repeated attribution across rules or within the same component must fail closed.
- Sum of event signed effects must equal component effect within explicit tolerance. This contract does not decide which candidate event is truly economic; proven source-row binding, event classification, scope, and economic ownership still require independent checks.
- A passing contract never grants MATCH, inventory adjustment, operator approval or WME posting rights.
- Six synthetic tests cover positive 00060-shaped three-row net -86.35, duplicate ownership across components, duplicate within component, document reused legitimately by distinct rows, mathematical mismatch, missing pointer.
- The previously documented real CORE output includes 00060 in timeline but not as structured contributing documents of INV-01. Strict xfail remains OPEN; current tests are only isolated structural rules.
- GOV-AT-05/06 economic-event ownership, ambiguity across matchers, partial split/netting, WME bridge, source staleness and versioned legacy report compatibility remain OPEN. GOV-002 OPEN. No merge; V1 NO_GO.
