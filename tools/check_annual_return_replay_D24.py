"""Recompute bounded annual project equity IRR from the reconciled synthetic ledger."""
from fractions import Fraction
import json
import sys

from check_operating_replay_D20 import ROOT, amount, require
from check_return_replay_D23 import replay_with_sources

sys.path.insert(0, str(ROOT / "src"))
from miniuw_foundation.investor_returns import parse_investor_returns
from miniuw_foundation.irr_checked_output import _current_annual_roots
from miniuw_foundation.primitive_periodic_returns import isolate_primitive_periodic_returns


def verify_irr(project_equity, compiled, story, saved):
    source = parse_investor_returns(json.dumps(compiled).encode("utf-8"))
    grid = source["grid"]
    parameters = source["irr_parameters"]
    calendar = project_equity["calendar"]
    require([row["date"] for row in calendar] == grid["dates"] and grid == saved["grid"]
            and parameters == saved["parameters"], "IRR calendar or parameters differ")

    width = amount(parameters["max_periodic_rate_interval_width"])
    splits = parameters["split_budget"]
    operations = parameters["operation_budget"]
    roots = isolate_primitive_periodic_returns([Fraction(row["net"]) for row in calendar], width, splits, operations)
    annual, attempted, blockers = _current_annual_roots(roots, parameters["periods_per_year"], grid["step_months"])
    require(roots == saved["primitive_roots"] == story["periodic_irr"]
            and roots["status"] == "complete_synthetic" and roots["selected_rate"] is None
            and roots["distinct_positive_discount_roots"] == 1 and not roots["unresolved_intervals"],
            "Replayed periodic IRR enclosure differs or is incomplete")
    require(annual == saved["annual_roots"] == story["annual_irr_roots"]
            and attempted == saved["attempted_annual_roots"] and blockers == saved["annualization_blockers"] == []
            and saved["point_rate_selected"] is False and story["selected_IRR"] is None,
            "Replayed annual IRR enclosure differs or a rate was selected")

    scaled = isolate_primitive_periodic_returns([Fraction(row["normalized_net"]) for row in calendar],
                                               width, splits, operations)
    require(scaled["status"] == roots["status"] and scaled["roots"] == roots["roots"]
            and not scaled["unresolved_intervals"] and scaled["selected_rate"] is None,
            "Normalizing equity changed the periodic IRR enclosure")
    return dict(month_step=grid["step_months"], periods_per_year=parameters["periods_per_year"],
                method=roots["method"], root_count=roots["distinct_positive_discount_roots"],
                annual_roots=annual, normalized_roots_match=True, selected_rate=None)


def run(root=ROOT):
    report, sources = replay_with_sources(root)
    for case, (compiled, story, saved) in zip(report["snapshots"], sources, strict=True):
        equity = case["project_equity"]
        equity["irr"] = verify_irr(equity, compiled, story, saved)
    return report


if __name__ == "__main__":
    try:
        print(json.dumps(run(), ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
