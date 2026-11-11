"""Calculate pilot YoC and spread from bound synthetic operating and cost inputs."""
from check_operating_replay_D20 import amount, require
from check_reference_package import PackageError
from check_yoc_spread_D70 import METRICS, compute, source_ref
from miniuw_foundation.debt_service import _date, rational
from miniuw_foundation.drafts import ValidationError
from worksheet_sale_rate_grid_D84 import money


CALCULATED_METRICS = {key: (unit, "scalar", None, definition) for key, (unit, definition) in METRICS.items()}
NOI_INVENTORY = {
    "income_rows": {"SYNTHETIC-income-residential", "SYNTHETIC-income-commercial"},
    "expense_rows": {"SYNTHETIC-expenses-excluding-tax"},
}
TDC_FIELDS = dict(context=None, currency=None, complete=None, scope_ref=None, rows=[])
CAP_FIELDS = dict(context=None, currency=None, period_ref=None, kind=None, value=None, source_ref=None)


def annual_period(period):
    if not isinstance(period, str) or period.count("/") != 1:
        return False
    try:
        start, end = (_date(day) for day in period.split("/"))
    except ValidationError:
        return False
    return start.day == end.day == 1 and start.month == end.month and end.year == start.year + 1


def yield_evidence(group, name, scenario):
    result = dict(values=dict.fromkeys(METRICS), blockers={key: [] for key in METRICS}, period_ref=None,
                  workbook_sha256=None, stabilized_noi=None, tdc=None, reference_cap=None)
    blocker = None
    if scenario["cash_per_usd_10"] is None:
        blocker = "current_scenario_cash_unavailable"
    elif group is None:
        blocker = "yield_inputs_missing"
    elif not isinstance(group, dict) or not group.keys() <= {"workbook_sha256", "stabilized_noi", "tdc", "cap_rate"}:
        blocker = "yield_source_fields_invalid"
    elif group.get("workbook_sha256") != scenario["preflight"]["workbook_sha256"]:
        blocker = "yield_workbook_revision_mismatch_or_missing"
    if blocker:
        return result | {"blockers": {"YoC": [blocker], "spread": [blocker, "yoc_unavailable"]}}

    result["workbook_sha256"] = group["workbook_sha256"]
    noi = group.get("stabilized_noi")
    context = scenario["context"] | {"scenario_id": f"SYNTHETIC-{name}"}
    if not isinstance(noi, dict) or noi.get("context") != context:
        blocker = "compatible_stabilized_noi_source_missing"
    elif not annual_period(noi.get("period_ref")):
        blocker = "stabilized_annual_period_missing_or_incompatible"
    else:
        result["period_ref"] = noi["period_ref"]
        for family, expected in NOI_INVENTORY.items():
            rows = noi.get(family)
            if (not isinstance(rows, list) or len(rows) != len(expected)
                    or any(not isinstance(row, dict) or not isinstance(row.get("item_id"), str)
                           or not source_ref(row.get("source_ref")) for row in rows)
                    or {row["item_id"] for row in rows} != expected):
                blocker = "stabilized_operating_inventory_missing_or_incompatible"
                break
    if blocker:
        return result | {"blockers": {"YoC": [blocker], "spread": [blocker, "yoc_unavailable"]}}

    # Nulls preserve missing inputs for the D70 calculator and allow an independent YoC when the cap is absent.
    try:
        tdc = TDC_FIELDS | (group.get("tdc") or {})
        cap = CAP_FIELDS | (group.get("cap_rate") or {})
        if isinstance(tdc["rows"], list):
            tdc["rows"] = [dict(component=None, amount=None, source_ref=None) | row for row in tdc["rows"]]
        calculated = compute(dict(stabilized_noi=noi, tdc=tdc, cap_rate=cap), result["period_ref"])
    except (ValidationError, PackageError, TypeError):
        blocker = "invalid_yield_source_or_source_metadata"
        return result | {"blockers": {"YoC": [blocker], "spread": [blocker, "yoc_unavailable"]}}
    return result | calculated


def yield_records(inventory, scenarios, case_sha256):
    inventory = {} if inventory is None else inventory
    require(isinstance(inventory, dict) and inventory.keys() <= scenarios.keys(),
            "Yield inputs must identify an explicit pilot scenario")
    values, evidence = [], {}
    for name, scenario in scenarios.items():
        result = yield_evidence(inventory.get(name), name, scenario)
        evidence[name] = result | dict(case_sha256=case_sha256, source_pointer=f"/yield_inputs/{name}")
        for metric, (unit, kind, currency, definition) in CALCULATED_METRICS.items():
            values.append(dict(metric_id=metric, scenario_id=name, definition_ref=f"SYNTHETIC-D70-{definition}",
                               unit=unit, quantity_kind=kind, currency=currency, period_ref=result["period_ref"],
                               applicability="applicable", applicability_evidence_ref=None, value=result["values"][metric]))
    return values, evidence


def display_yield(metric, value):
    if value is None:
        return "PENDING"
    if metric == "YoC":
        return f"{money(rational(amount(value) * 100))}%"
    return f"{money(value)} bps"
