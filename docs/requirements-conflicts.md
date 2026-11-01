# Current requirements and source conflicts

Current authority is the user's supplied handoff (sections shown below). Historical documents retain their original claims; later filenames/dates and document role labels do not settle disagreements. The resolutions below implement current explicit user instructions, not invented financial policy. All financial definitions remain subject to model review.

## Current requirements

| ID | Requirement | Current evidence |
|---|---|---|
| REQ-01 | Model review before production underwriting, real deals or deployed bots | Handoff §§3, 8, 11 |
| REQ-02 | Exactly one external decision PDF page; internal audit records allowed | Handoff §2 |
| REQ-03 | Investment thresholds start empty per deal and are explicitly supplied, separate from bank conditions | Handoff §§3, 6 |
| REQ-04 | Required missing/conflicting data blocks affected results; explicit zero remains zero; undefined remains unresolved | Handoff §3 |
| REQ-05 | Preserve originals, sources, formula definitions, units, periods, dependencies and alternate conflict claims | Handoff §§4, 7 |
| REQ-06 | Explicit scenario parameters, applicability, comparison/equality and aggregation rules; no automatic Base copying | Handoff §6 |
| REQ-07 | Immutable execution snapshots and atomic current-revision checks for decisions/publication | Handoff §7 |
| REQ-08 | Separate original evidence, normalized inputs, calculations, decision comparisons, human review and rendered PDF | Handoff §7 |
| REQ-09 | Full UW requires an applicable current PASS plus authentic final approval; a name/checkbox/boolean is insufficient | Handoff §§2, 3, 7 |
| REQ-10 | No contact with Lorena now; consolidate only questions that cannot be resolved from evidence | Handoff §§3, 11 |
| REQ-11 | Ordinary milestone commits/pushes authorized; preserve work; verify full remote SHA and omissions | Handoff §10 |

## Findings

| ID | Alternate claims and exact source locations | Current handling / unresolved work |
|---|---|---|
| CUR-01 | Master v5.1 §§4–5 and D1 p. 3 contain fixed scenario/approval tables; Input Sheet Inputs!A2 points to prompt thresholds. Handoff §§3, 6 requires fresh explicit deal criteria and configured scenarios. | Historical numbers remain in original archives only. New active criteria stay empty. Scenarios require explicit provenance/configuration; do not activate inherited shocks. |
| CUR-02 | Master §0/§7, Manual pp. 3–4, roadmap p. 5 Q20 and decision package paragraph 22 retain PDF + Excel + summary by default. Handoff §2 requires exactly one PDF page externally. | Current external requirement prevails. Internal backups/audit may be retained. Historical Q20 A is not an active override. |
| SRC-01 | Standards policy 4 permits auditable area takeoff; Master §1(7), Manual p. 19 and decision package F0-02 prohibit reconstructed GBA. | Current handoff defers inferred CAD measurements and forbids invented inputs. No takeoff implemented. Retain both claims for source-authority review. |
| SRC-02 | Master §3 break-even denominator is gross potential income; Manual p. 19 says effective income; Standards policy 11 defines an occupancy condition without a complete revenue/cost function. | Formula blocked pending explicit revenue, vacancy/concessions, operating costs, property-tax and debt-service treatment. Do not choose one ratio silently. |
| SRC-03 | Master §3 RLV uses two target metrics; Standards policy 13 refers to development, financing and equity-return requirements; Q3 is unresolved (roadmap p. 5; Manual p. 22). “Asking over RLV” has no uniquely approved formula. | Two-target supported price is not certified house RLV/Q3. Separate asking, evaluated purchase price and supported-price domain. Define sign/zero/negative boundary handling and attainability. |
| SRC-04 | Master §1A/§3 embeds tax exemption and timing assumptions; Q2 and PAR-03/04 remain unresolved. | Treat legal assertions as unverified historical claims, not current tax advice. Verify current official legal sources at a later legal-rule review before any adoption; no legal conclusion made here. |
| SRC-05 | Master §3 and Standards policies 9–16 require equity/CoC/IRR/EM with partly unresolved denominators and calendars; Q6–Q8, Q12–Q13 open. | Specify gross contributions/distributions, reserve restrictions, cash-in and debt versus investor payout; no net-flow sign shortcut for EM. Undefined CoC or IRR remains unresolved. |
| SRC-06 | Input Sheet is claimed current; package refers to missing v5.2 DRAFT; decision package paragraph 33 mentions 40 None/empty-string differences. | Original 55 fields verified. No DRAFT workbook or comparison artifact is available, so those 40 differences are not reproduced. Preserve raw blanks and source metadata. |
| SRC-07 | 1101 preview is one PDF page and says NOT CALCULATED; extracted header reads “PREVIEW · NOT CALCU”. Underlying plans are absent. | Page count verified, visual legibility/clipping and original deal facts unverified. Do not certify this as a validated production PDF. |
| REC-01 | Historical document ZIP v2.2 versus cloud recovery revision 34/75 base files reported in handoff. | Different artifacts. Recovery payload/installer/startup missing; source documents do not restore reference code. |
| REC-02 | A recovered XLSX is labeled Input Sheet, while a Full UW Excel is mentioned historically. | Only blank Inputs workbook recovered; Full UW model missing. |
| REC-03 | Different roadmap binary hashes, identical extracted text. | Retain both binaries; text equality does not prove visual identity or authority. |
| REC-04 | D1 p. 2 refers to 03_modulos_y_dependencias.md; p. 4 says Full UW workbook absent. | Referenced module file and Full UW model not attached. Initial module map here is a draft. |
| REC-05 | Process v0.3.0 pp. 1–7 describes implemented modules and 117 tests. | Descriptive historical evidence only; no matching implementation recovered on this host. |
| REC-06 | Handoff lists PC-01–PC-07 but no descriptions. | Keep open without invented definitions. New IDs above are separate. |
| REC-07 | Prior references report test counts and conditional price monotonicity. | No runnable references recovered; no independent financial validation or supported-price certification. |
| REC-08 | Feedback p. 1 proposes seven Dots; Manual pp. 34/37 and roadmap p. 4 define 16 per-deal bots plus test bot 17; Process pp. 6–7 maps seven Dots to 17 roles. | Functional groupings can differ in granularity. This reconciles documentary counts, not deployed agents. No deployment evidence recovered; architecture remains proposed. |

No findings above close historical PC-01–PC-07, certify Phase 0, authenticate expert decisions, or authorize production.
