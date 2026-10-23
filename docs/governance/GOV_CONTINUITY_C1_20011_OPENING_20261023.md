# GOV C1 — Article 20011 opening-balance source audit (2026-10-23)

Status: Read-only SOURCE_ARITHMETIC_VERIFIED / ECONOMIC_CAUSE_REVIEW; G0 OPEN / CORE NO_GO.

Source WME: Fisa_magazie_WME_2025-12-27_2026-10-11_export_2026-10-11.XLSX; SHA256 735b4756045ae0c5d22e01beb3d77430e105a939c2cbf8b6f0bf28ac3e041495.

WME item 1492 StocInitial rows 96997, 96998, 96999 (2025-12-27) have balances 19279, 94279, 94279 BUC, zero in/out. These are NOT three receipts; never sum the snapshots.

WME 46 BC rows 97000–97045 between Dec 27–31 consume 18452 BUC (daily 1264, 5256, 7016, 2964, 1952); last 2025-12-31 row 97045 balance 75827 BUC. Arithmetic 94279 - 18452 = 75827, confirmed.

WMS source Stoc_initial_WMS_2026-01-01.xlsx: row with article 20011, date 2026-01-01 00:00, opening 75227 BUC. Opening boundary WMS minus last 2025 WME = 75227 - 75827 = -600 BUC.

Caveat: WME has last Dec 31 reported balance, not a separately confirmed Jan 1 snapshot; full warehouse/management scope alignment and cause of -600 require operator/source checks. Earlier WME StocInitial transition 19279 -> 94279 is NOT attributed to a physical movement.

Do not attribute final 2026-10-11 stock difference to October COR STOC or to -600 alone; preserve REVIEW.

Archive inventory: CURRENT_STATUS.md stores summary G1 D2–D10; detailed local attachments exist in conversation runtime, but this is not durable project archival. Drive metadata search for G1-D yielded zero matching names; cannot claim absent under other filenames. Prior older 20011 reports in Drive must not be conflated with G1 evidence. No raw private exports written to Git.

Next: resolve opening warehouse scope and StocInitial semantics with source evidence and operator, then implement persistent case/decision registers only with reviewed permissions. No CORE code edits, no MATCH.