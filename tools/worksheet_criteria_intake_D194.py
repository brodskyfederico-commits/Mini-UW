"""Read the version-bound Lorena workbook into the D193 comparison contract."""
from hashlib import sha256

from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.threshold_rehearsal import ROWS
from preview_lorena_criteria_D192 import SHEET, parse_condition, read_cells
from worksheet_definition_screening_D193 import RLV
from worksheet_local_sources_D127 import object_or_empty, synthetic_id


SCENARIOS = ("Base", "Downside")
METRIC_IDS = {metric for _, metric in ROWS}
CONTEXT_FIELDS = {"scenario_id", "metric_id", "definition_ref", "unit", "period_ref"}
LAND_BAND_LITERAL = "> banda RLV"


def compile_criteria(case, raw):
    binding = object_or_empty(case.get("criteria_workbook"))
    observed = sha256(raw).hexdigest() if raw is not None else None
    result = dict(worksheet=SHEET, expected_sha256=binding.get("sha256"), observed_sha256=observed,
                  criteria_revision=case.get("criteria_revision"), rules=[], rows=[], derived_rlv=[],
                  blockers=[], criteria_adopted=False)

    def blocked(reason):
        result["blockers"].append(reason)
        return result

    if raw is None:
        return blocked("criteria_workbook_missing")
    if observed != result["expected_sha256"]:
        return blocked("criteria_workbook_hash_mismatch")
    try:
        cells = read_cells(raw)
    except ValidationError as error:
        return blocked(f"criteria_workbook_invalid:{error}")
    declared = cells.get("B18")
    if not synthetic_id(declared) or declared != case.get("criteria_revision"):
        return blocked("criteria_workbook_revision_mismatch")
    result.update(source_revision_cell="B18", source_revision_literal=declared,
                  downside_policy_note=cells.get("B19") or None)

    contexts = case.get("rules")
    if not isinstance(contexts, list) or len(contexts) > len(ROWS) * len(SCENARIOS):
        return blocked("criteria_workbook_comparison_context_invalid")
    indexed = {}
    for item in contexts:
        if (not isinstance(item, dict) or item.keys() != CONTEXT_FIELDS
                or any(not isinstance(value, str) or not value.strip() for value in item.values())
                or item["scenario_id"] not in SCENARIOS or item["metric_id"] not in METRIC_IDS):
            return blocked("criteria_workbook_comparison_context_invalid")
        identity = item["scenario_id"], item["metric_id"]
        if identity in indexed:
            return blocked("criteria_workbook_comparison_context_duplicate")
        indexed[identity] = item

    for row_num, (_, metric) in enumerate(ROWS, 7):
        for scenario, columns in zip(SCENARIOS, ("EF", "GH"), strict=True):
            context = indexed.get((scenario, metric))
            reasons, conditions, provenance = [], {}, {}
            for mode, col in zip(("pass", "fail"), columns, strict=True):
                address = f"{col}{row_num}"
                literal = cells.get(address, "")
                provenance[mode] = dict(cell=address, literal=literal)
                if metric == RLV and mode == "fail" and literal.casefold() == LAND_BAND_LITERAL.casefold():
                    conditions[f"{mode}_condition"] = dict(operator=">", threshold=None)
                    continue
                parsed = parse_condition(literal)
                if not literal:
                    reasons.append(f"{mode}_condition_missing")
                elif literal.casefold() == "no aplica":
                    reasons.append("applicability_unconfirmed")
                elif literal.casefold() == "sin fail":
                    reasons.append("pass_only_policy_unconfirmed_for_D193")
                elif parsed is None:
                    reasons.append(f"{mode}_condition_invalid")
                elif context is not None and parsed[1] != context["unit"]:
                    reasons.append(f"{mode}_condition_unit_mismatch")
                else:
                    conditions[f"{mode}_condition"] = parsed[0]
            if context is None:
                reasons.append("comparison_context_missing")
            note_ref = f"I{row_num}"
            entry = dict(scenario_id=scenario, metric_id=metric, conditions=provenance,
                         note_cell=note_ref, note=cells.get(note_ref, ""), blockers=sorted(set(reasons)))
            if not reasons:
                entry["rule_index"] = len(result["rules"])
                result["rules"].append(context | conditions)
                if conditions["fail_condition"]["threshold"] is None:
                    result["derived_rlv"].append(scenario)
            result["rows"].append(entry)
    return result
