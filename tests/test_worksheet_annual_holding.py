"""Check annual post-refinance holding from the synthetic worksheet and its audit."""

from argparse import ArgumentParser
from copy import deepcopy
from datetime import date
from fractions import Fraction
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_worksheet_florida_tax_D203 import settings_for_tax
from check_worksheet_technical_acceptance_D200 import source_files
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, WORKBOOK_CRITICAL_EVIDENCE_SCHEMA, deliver_package, read_package
from worksheet_annual_coc import quantity as amount
from worksheet_calendar_routes_D199 import route_cash
from worksheet_intake_D198 import assemble, register
from worksheet_project_calendar_D145 import offset


ROUTE = "annual_hold_with_refinance"


def annual_settings():
    settings = settings_for_tax() | {"schema": WORKBOOK_CRITICAL_EVIDENCE_SCHEMA}
    inputs = settings["rent_inputs"]
    routes = inputs["calendar_checks"] = {}
    for name, nois, forward in (("Base", (91_000, 99_000, 105_000, 112_000), 400_000),
                                ("Downside", (44_000, 50_000, 55_000, 60_000), 205_000)):
        sale = date.fromisoformat(inputs["supplemental_scope"][name]["sale_date"]["value"])
        dates = [offset(sale, n) for n in (0, 3, 6, 9)]
        start = offset(dates[-1].replace(day=1), 1)
        source = f"SYNTHETIC-D234-{name}-annual-hold"
        terms = dict(route="interest_only_then_amortize", source_ref=source, interest_only_payments=1,
                     amortization_clock="count_interest_only_inside_original_amortization", sale_payment_index=4,
                     requested_principal=dict(value=rational(1_200_000), source_ref=f"{source}/bank"),
                     construction_tax=dict(applicability="no_incremental_tax_in_variant", source_ref=f"{source}/fiscal-scope"),
                     delayed_forward_noi=dict(value=rational(forward), noi_basis="before_replacement_reserves",
                                              period_ref=f"{start}/{offset(start,12)}", source_ref=f"{source}/sale"),
                     quarterly_noi_before_reserves={d.isoformat(): dict(value=rational(v), source_ref=f"{source}/{d}")
                                                   for d, v in zip(dates, nois, strict=True)})
        routes[name] = {ROUTE: terms}
    return settings


def reconcile(route, view, terms):
    assert route["state"] == "calculated_synthetic"
    proof = route["annual_post_refi_coc"]
    assert proof["state"] == "calculated_synthetic"
    rows, scale = route["cash_by_period"], amount(view["cash_per_usd_10"]["scale_factor"])
    operation = [row for row in rows if row["stage"] == "operation"]
    schedule = route["debt"]["schedule"]
    assert [r["date"] for r in operation] == list(terms["quarterly_noi_before_reserves"])
    assert [r["phase"] for r in schedule] == ["interest_only", "amortizing", "amortizing", "amortizing"]
    assert [r["date"] for r in schedule] == [r["end"] for r in proof["quarters"]]
    annual_noi = sum(amount(x["value"]) for x in terms["quarterly_noi_before_reserves"].values())
    reserve = amount(view["replacement_reserve"]["deposit"])
    service = sum(amount(r["service"]) for r in schedule)
    available = sum(amount(r["distribution"]) - amount(r["contribution"]) for r in operation)
    assert available == annual_noi - reserve - service == amount(proof["cash_available"])
    for index, row in enumerate(operation):
        deposit = amount(row["closing_restricted"]) - amount(row["opening_restricted"])
        assert deposit == (reserve if index == 3 else 0)
        assert amount(proof["quarters"][index]["scheduled_service"]) == amount(schedule[index]["service"])
    remaining = sum(amount(r["contribution"]) for r in rows if r["stage"] == "construction") - next(
        amount(r["distribution"]) for r in rows if r["stage"] == "refinance")
    assert remaining == amount(proof["equity_remaining"]) and available / remaining == amount(proof["value"])
    assert route["sale"]["date"] == schedule[-1]["date"] and route["sale"]["principal_paid"] == schedule[-1]["closing"]
    for row in rows:
        assert sum(amount(row[k]) for k in ("opening_free", "opening_restricted", "sources")) == sum(
            amount(row[k]) for k in ("uses", "closing_free", "closing_restricted"))
    cash = route["cash_per_usd_10"]
    assert amount(rows[0]["contribution"]) * scale == 10
    assert sum(amount(r["distribution"]) for r in rows) * scale == amount(cash["received"])
    assert sum(amount(r["contribution"]) for r in rows) * scale == 10 + amount(cash["additional"])
    assert max(Fraction(), 10 + amount(cash["additional"]) - amount(cash["received"])) == amount(cash["unrecovered"])
    return dict(coc=proof["value"], sale=route["sale"]["date"], cash=cash)


def verify(root):
    settings = annual_settings()
    sources = source_files(root / "sources")
    package, revision = root / "expediente", root / "vigente.json"
    assembled = assemble(settings, register(sources, "SYNTHETIC-D234-annual-hold"), sources, package)
    assert assembled["decision"] == "PENDING" and not assembled["source_blockers"]
    saved = read_package(package)
    revision.write_bytes(saved[CURRENT_REVISION_FILE])
    result = json.loads(saved["results.json"])
    assert result["decision"] == "PENDING" and not result["real_decisions_enabled"] and not result["deployment_enabled"]
    summaries = {}
    for name, view in result["scenarios"].items():
        terms = settings["rent_inputs"]["calendar_checks"][name][ROUTE]
        route = result["calendar_checks"][name][ROUTE]
        summaries[name] = reconcile(route, view, terms)
        changed = deepcopy(terms)
        dict_noi = changed["quarterly_noi_before_reserves"]
        day = next(iter(dict_noi))
        dict_noi[day]["value"] = None
        blocked = route_cash(view, changed)
        assert blocked["blocker"] == "four_documented_noi_quarters_after_refinancing_required"
        assert blocked["cash_per_usd_10"] is None
        dict_noi[day]["value"] = rational(0)
        assert route_cash(view, changed)["annual_post_refi_coc"]["quarters"][0]["noi_after_reserves"] == rational(0)
        changed["requested_principal"]["value"] = rational(50_000_000)
        capped = route_cash(view, changed)
        assert capped["blocker"] == "selected_principal_exceeds_declared_bank_capacity" and capped["cash_per_usd_10"] is None
    delivery = deliver_package(package, root / "MiniUW_Vigente.pdf", revision)
    assert delivery["decision"] == "PENDING" and read_package(package) == saved
    return dict(status="passed", decision="PENDING", delivery=delivery, annual=summaries)


class WorksheetAnnualHoldingTests(TestCase):
    def test_annual_hold_replays_from_the_synthetic_worksheet(self):
        with TemporaryDirectory(prefix="miniuw-annual-hold-") as tmp:
            self.assertEqual(verify(Path(tmp))["status"], "passed")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir()
    print(json.dumps(verify(args.output), ensure_ascii=False))
