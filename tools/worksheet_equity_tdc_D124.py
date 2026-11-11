"""Reconcile applied synthetic funding to the pilot's current all-in budget."""
from check_equity_tdc_D71 import reconcile
from check_operating_replay_D20 import require
from check_reference_package import PackageError
from miniuw_foundation.debt_service import _date
from miniuw_foundation.drafts import ValidationError


METRIC_ID = "equity_TDC"
DEFINITION = "SYNTHETIC-D71-applied-equity-over-complete-tdc"
METRIC = ("fraction", "scalar", None, DEFINITION)


def funding_evidence(group, budget):
    result = dict(state="PENDING", blockers=[], equity_to_tdc=None, applied_funding=None, cutoff=None,
                  debt_commitment=None, tdc=budget["tdc"], tdc_source_sha256=budget.get("tdc_source_sha256"),
                  workbook_sha256=budget["workbook_sha256"], funding_source_sha256=None, decision="PENDING")
    if budget["tdc"] is None:
        blocker = "positive_complete_pilot_tdc_required"
    elif not isinstance(group, dict) or not group.keys() <= {"workbook_sha256", "tdc_source_sha256", "funding"}:
        blocker = "applied_funding_source_missing_or_invalid"
    elif group.get("workbook_sha256") != budget["workbook_sha256"]:
        blocker = "funding_workbook_revision_mismatch_or_missing"
    elif group.get("tdc_source_sha256") != budget["tdc_source_sha256"]:
        blocker = "funding_tdc_revision_mismatch_or_missing"
    else:
        funding = group.get("funding")
        if not isinstance(funding, dict):
            return result | {"blockers": ["applied_funding_source_missing_or_invalid"]}
        try:
            cutoff = _date(funding.get("cutoff"))
            result["cutoff"] = cutoff.isoformat()
            if cutoff >= _date(budget["period_ref"].split("/")[0]):
                return result | {"blockers": ["funding_cutoff_must_precede_stabilized_period"]}
            return result | reconcile(funding, budget, result["cutoff"])
        except (ValidationError, PackageError, TypeError):
            blocker = "applied_funding_inputs_missing_or_invalid"
    return result | {"blockers": [blocker]}


def equity_records(inventory, budgets, case_sha256):
    inventory = {} if inventory is None else inventory
    require(isinstance(inventory, dict) and inventory.keys() <= budgets.keys(),
            "Funding inputs must identify an explicit pilot scenario")
    values, evidence = [], {}
    for name, budget in budgets.items():
        result = funding_evidence(inventory.get(name), budget)
        evidence[name] = result | dict(case_sha256=case_sha256, source_pointer=f"/funding_inputs/{name}",
                                       tdc_pointer=f"/screening/yield_by_scenario/{name}/tdc")
        values.append(dict(metric_id=METRIC_ID, scenario_id=name, definition_ref=DEFINITION, unit="fraction",
                           quantity_kind="scalar", currency=None, period_ref=result["cutoff"],
                           applicability="applicable", applicability_evidence_ref=None, value=result["equity_to_tdc"]))
    return values, evidence
