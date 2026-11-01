# Mini-UW — source recovery and model review

Private project repository: https://github.com/brodskyfederico-commits/Mini-UW

Product coding, real-deal underwriting and Dots/Bots deployment remain paused. This milestone preserves the supplied source documents and records what is verified, proposed, conflicting or missing. It does not restore or certify the original application.

Start with [recovery status](docs/recovery-status.md), [requirements and conflicts](docs/requirements-conflicts.md), [source register](docs/source-register.json), [model design](docs/model-design.md), and [work log](WORK_LOG.md). Original bytes are in `sources/originals/`; hashes and each attachment/ZIP-member location are in the register. Extracted text is a reading aid, not an authenticated or visually certified copy.

The current product requirement is exactly one external decision PDF page. Investment thresholds begin empty for every deal. Historical thresholds and scenario tables are archived as evidence, never installed as defaults. The workbook is a blank 55-field Input Sheet, not a Full UW model.

GitHub records reviewed milestone files and infrastructure definitions. Runtime services, databases, credentials and live deal data are not automatically backed up by this repository. No deployment or scheduled synchronization is configured.

Latest model review: [coverage matrix and evidence guide](docs/coverage-guide.md), [full CSV](docs/coverage-matrix.csv), and [cash/capital contracts](docs/model-cash-contracts.md). The matrix inventories 398 items and certifies no end-to-end product coverage.

Continued Mini-UW model: [M2 operations/NOI contracts](docs/model-operations-contract.md). Full UW is deferred until the end per current user direction.

New review: [budget and schedule](docs/model-budget-schedule.md), [Lorena input/decision contract](docs/decision-input-contract.md), [module closure gates](docs/module-closure.md).

Construction finance: [M5 debt/interest/equity contracts](docs/model-construction-finance.md), with bounded isolated algebraic evidence.

Professional review: [Spanish structure PDF, R01, 26 pages](docs/review/MiniUW_Estructura_para_Revision_Profesional.pdf). Conceptual model review with sources/open decisions; no implementation code or real-deal evaluation.

Refinancing: [M6 permanent debt, sizing, payoff and cash contracts](docs/model-refinance-contract.md). This expands the preliminary M6 structure after the preserved professional PDF R01 cutoff; it is not expert approval.

Hold, exit and returns: [M7 operating cash, sale and investor-return contracts](docs/model-hold-exit-returns.md). The professional PDF R01 remains the earlier snapshot.

Scenarios and price: [M8 explicit scenario configuration and price-domain contracts](docs/model-scenarios-price.md). No historical shocks/criteria or global optimum are activated/certified.

Decision and audit: [M9 comparison, pending-state, authenticated-review and publication contracts](docs/model-decision-audit.md). Hypothetical reference aggregation is not house policy.

Input/evidence contracts: [M1](docs/model-input-evidence.md), [55-field proposed contract map](docs/input-contract-map.json), [source reconciliation limits](docs/source-review-limits.md), and [36 acceptance specifications](docs/acceptance-case-contracts.json). None implies product certification.

[Independent specification package status](docs/integration-and-readiness.md) separates prepared design deliverables from still-open expert, financial-validation and production gates. No model-complete or production-ready claim is made.

Current professional review: [R02 PDF, 29 pages](docs/review/MiniUW_Estructura_para_Revision_Profesional_R02.pdf). R01 retained unchanged. R02 reflects the full candidate-contract specification, not a production-ready or expert-approved model.

Post-R02 independent work: [revision/scenario integrity](docs/revision-scenario-integrity.md) and [feedback intake protocol](docs/feedback-intake-protocol.md). The [blank feedback template](docs/professional-feedback-template.csv) records no review responses; R02 remains unchanged.

Continued independent structure: [module interface protocol](docs/module-interface-protocol.md), [record contracts](docs/record-contracts.md), [execution design](docs/execution-structure-guide.md), [draft schemas](schemas/README.md), and [intentionally empty project template](templates/project-draft-empty.json). Structural checks do not close financial/professional gates.

Calendar/accounting structure: [calendar and cash/debt/accrual ledger contracts](docs/calendar-ledger-contracts.md), with an explicitly synthetic fixture and retained balance discrepancies. No bank timing/interest policies are selected.

Scope/evidence structure: [cost-scope reconciliation](docs/cost-scope-reconciliation.md) prevents counting the same explicitly mapped economic scope twice and preserves conflicting claims. [Evidence locators](docs/evidence-locator-contract.md) bind literal PDF/Word/Excel citations to inventoried source bytes; matching a citation does not validate its meaning or authority.

Cross-module structure: [budget-period-payment bridge](docs/budget-payment-bridge.md) links explicit M3 scopes, M4 allocations and M5 cash records. Forty-one synthetic controls retain discrepancies and unmapped amounts; no schedule, accrual policy or actual financing is inferred.

Further independent references: [content-bound calculation lineage](docs/calculation-lineage.md) detects changes beyond revision labels and preserves transitive blockers. [Periodic IRR root isolation](docs/periodic-irr-root-isolation.md) counts and bounds all positive discount-factor roots with explicit work/precision inputs; it selects no rate and does not activate financial screening.

Continued integration references: [gross investor cash, return grid and interval comparison](docs/investor-return-bridges.md) preserve empty points, multiple roots and pending refinements. [Package check runbook](docs/reference-check-runbook.md) provides a read-only integrity check and temporary-copy execution of 18 synthetic suites, with a GitHub Actions workflow. A saved workflow is not evidence of remote success.

First remote workflow success is recorded in [CI verification](docs/ci-verification.json), tied to its exact tested commit. It does not certify later commits or financial/model completeness.

Further cash integration: [operating and settlement bridges](docs/operating-settlement-bridges.md) reconcile declared accrued NOI/working balances to cash and explicit gross-cash sale/refinance closings to debt/obligations/reserves. Net-withheld, partial-discharge and unsupported adjustments remain pending. The package checker now registers 20 scoped reference suites.
