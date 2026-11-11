"""Bind supplied synthetic metrics to the exact workbook revision used by the pilot."""
from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction
from miniuw_foundation.drafts import ValidationError


REFERENCE_METRICS = {
    "YoC": ("fraction", "scalar", None, "stabilized-noi-over-declared-tdc"),
    "spread": ("bps", "scalar", None, "yoc-less-reference-cap-in-bps"),
    "breakeven_occupancy": ("fraction", "scalar", None, "economic-occupancy-for-debt-service"),
    "post_refi_CoC": ("fraction", "scalar", None, "annual-post-refi-cash-over-declared-equity"),
    "equity_TDC": ("fraction", "scalar", None, "applied-equity-over-complete-tdc"),
    "IRR": ("fraction", "scalar", None, "annualized-periodic-irr-supplied-reference"),
    "asking_relative_to_supported_price": ("multiple", "scalar", None, "asking-over-supported-price"),
}

REFERENCE_LABELS = {
    "YoC": "Yield on Cost", "spread": "Spread",
    "breakeven_occupancy": "Ocupación de equilibrio", "post_refi_CoC": "CoC pos-refi",
    "equity_TDC": "Equity / TDC", "IRR": "TIR anual",
    "asking_relative_to_supported_price": "Asking / precio soportado",
}


def reference_records(inventory, scenarios, case_sha256):
    inventory = {} if inventory is None else inventory
    require(isinstance(inventory, dict) and inventory.keys() <= scenarios.keys(),
            "Reference metrics must identify an explicit pilot scenario")
    values, sources = [], []
    for name, scenario in scenarios.items():
        group = inventory.get(name)
        group = {} if group is None else group
        require(isinstance(group, dict) and group.keys() <= {"workbook_sha256", "claims"},
                "Reference claims require their worksheet revision")
        claims = group.get("claims")
        claims = {} if claims is None else claims
        require(isinstance(claims, dict) and claims.keys() <= REFERENCE_METRICS.keys(),
                "Only the declared synthetic reference metrics may be supplied")
        current_hash = scenario.get("preflight", {}).get("workbook_sha256")
        for metric, (unit, kind, currency, definition) in REFERENCE_METRICS.items():
            claim = claims.get(metric)
            claim = {} if claim is None else claim
            require(isinstance(claim, dict) and claim.keys() <= {"definition_ref", "unit", "period_ref", "value", "source_ref"},
                    "Use explicit reference metric claim fields")
            reference = f"SYNTHETIC-D121-{definition}"
            period = claim.get("period_ref")
            source = claim.get("source_ref")
            blockers = []
            if scenario["cash_per_usd_10"] is None:
                blockers.append("current_scenario_cash_unavailable")
            if current_hash is None or group.get("workbook_sha256") != current_hash:
                blockers.append("reference_workbook_revision_mismatch_or_missing")
            if claim.get("definition_ref") != reference or claim.get("unit") != unit:
                blockers.append("reference_definition_or_unit_missing_or_incompatible")
            if not isinstance(period, str) or not period.strip():
                blockers.append("reference_period_missing")
            if not isinstance(source, str) or not source.startswith("SYNTHETIC-D121-"):
                blockers.append("explicit_synthetic_reference_source_missing")
            value = claim.get("value")
            try:
                if _fraction(value) is None:
                    blockers.append("reference_value_missing")
            except ValidationError:
                blockers.append("reference_value_invalid")

            values.append(dict(metric_id=metric, scenario_id=name, definition_ref=reference, unit=unit,
                               period_ref=period if isinstance(period, str) and period.strip() else None,
                               quantity_kind=kind, currency=currency, applicability="applicable",
                               applicability_evidence_ref=None, value=None if blockers else value))
            sources.append(dict(metric_id=metric, scenario_id=name, origin="supplied_synthetic_reference",
                                case_sha256=case_sha256, claim_pointer=f"/reference_metrics/{name}/claims/{metric}",
                                workbook_sha256=group.get("workbook_sha256"), source_ref=source,
                                state="PENDING" if blockers else "declared_synthetic_value", blockers=blockers))
    return values, sources
