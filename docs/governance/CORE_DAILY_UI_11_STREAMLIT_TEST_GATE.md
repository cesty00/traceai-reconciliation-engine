CORE-DAILY-UI-11 — 2026-10-22
Status: TEST HARNESS COMMITTED / CI NOT YET VERIFIED
Previous workflow #1496 initially queued, pytest and daily gate observed success; check complete status separately.
Local Streamlit unavailable. Added synthetic Streamlit AppTest asserting the actual app loads an operator JSON plus nested investigation JSON, renders document 00060, shows UNVERIFIED, and exposes no approval button. Base pytest suite skips only the UI test if optional Streamlit absent; separate GitHub workflow installs .[dev,ui] and runs AppTest. AppTest is headless component execution, NOT an actual browser screenshot/responsive visual inspection. No real company sources committed. PR #69 remains Draft/unmerged, GOV-002/GOV-AT-05/06 OPEN and V1 NO_GO.
