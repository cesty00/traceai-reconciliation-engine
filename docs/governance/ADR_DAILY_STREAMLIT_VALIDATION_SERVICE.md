# ADR — Daily UI and human-validation security architecture
Date: 2026-10-21
Decision: RECOMMENDED DESIGN, NOT DEPLOYMENT APPROVAL

## Recommended split
1. CORE Python reconciliation engine remains independent and read-only for operational systems.
2. Streamlit is the preferred lightweight Daily presentation frontend, initially read-only. It is not currently established as a working component on this branch.
3. A separate validation API/service is the only writer to the audit datastore. Its server verifies OIDC identity and case-scoped role permissions; never trusts arbitrary browser/client claims or forwarded headers without a verified authenticated proxy boundary.
4. The persistent audit store uses transactional append-only review events with optimistic revision checks and monitored backups. Existing SQLiteReviewAudit is a synthetic prototype and is not ready for deployment.
5. Economic reconciliation and human documentary confirmation use independent status dimensions. Approval never authorizes WMS/WME mutation or forces MATCH.

## Rollout stages
A. Read-only operator screen driven by existing Daily case JSON; no reviewer login/approval controls.
B. Confirm deployment environment and real identity provider, identity claims, group-to-role mapping and case access.
C. Build and test a secured validation API with verified principals, source SHA/physical row checks, evidence scope and permanent audit integrity.
D. Pilot PV 1178 with WMS historical inventories in app, verified documents and staff roles. Permit CONFIRMED_LINK only after review; economic REVIEW remains independently controlled.
E. Evaluate performance and sign-off. No CORE merge/release until governance acceptance.

## Blocking unknowns
Actual Streamlit hosting environment; OIDC provider/tenant; reviewer roles and case ownership; deployment security controls; auditable backup/retention; source document access policy. No fake session implementation to bridge these unknowns.

## Current posture
PR #68 Draft, GOV-002 and GOV-AT-05/06 OPEN, V1 Daily NO_GO. Prior CI #1419 completed SUCCESS 4/4.
