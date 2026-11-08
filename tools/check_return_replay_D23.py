"""Reconcile gross project equity cash from the integrated synthetic replay."""
from collections import defaultdict
from fractions import Fraction
import json
import sys

from check_debt_sale_replay_D21 import CASE_CHAIN, STRUCTURE, digest, verify_amounts
from check_integrated_replay_D22 import run as replay_lifecycle
from check_operating_replay_D20 import ROOT, amount, local_file, require, resolve


REGISTER = STRUCTURE + "MiniUW_Calendario_y_Retorno_D16.json"
CATEGORIES = {
    "initial_capital", "additional_capital", "refinance_cash_in", "operating_distribution",
    "net_refinance_distribution", "net_sale_distribution", "other_distribution",
}
EVENT_FIELDS = ("date", "kind", "category", "currency")


def indexed(rows, field):
    result = {row[field]: row for row in rows}
    require(len(result) == len(rows), f"Duplicate {field}")
    return result


def reconcile_events(cash_events, investor, binding, compiled, story, snapshot):
    sources = indexed(cash_events, "source_event_id")
    slots = indexed(binding["preopening_slots"] + binding["operating_slots"], "investor_event_id")
    declared = indexed(investor["events"], "event_id")
    saved = indexed(story["events"], "event_id")
    archived = indexed(snapshot["event_rows"], "event_id")
    require(len(declared) == len(sources) == 8 and slots.keys() == declared.keys() == saved.keys() == archived.keys()
            and len(binding["preopening_slots"]) == 2 and len(binding["operating_slots"]) == 6
            and compiled == (investor | {"events": story["events"]}), "Equity event inventory differs")

    events = []
    for event_id, target in declared.items():
        source_id = slots[event_id]["source_event_id"]
        source = sources.pop(source_id) | {"currency": "USD"}
        row = archived[event_id]
        value = Fraction(source["amount"])
        require(target["amount"] is target["source_ref"] is None, f"Filled original equity slot: {event_id}")
        require(row["source_event_id"] == source_id and row["explicit_zero"] is (value == 0)
                and all(source[key] == target[key] == row[key] == saved[event_id][key] for key in EVENT_FIELDS)
                and saved[event_id]["source_ref"] == row["event_source_ref_string"]
                and amount(row["amount"]) == value == amount(saved[event_id]["amount"]) >= 0,
                f"Equity event differs: {event_id}")
        events.append(dict(source, event_id=event_id))
    require(not sources, "Unbound source equity event")
    return events


def totals(events):
    contributions = sum((Fraction(event["amount"]) for event in events if event["kind"] == "contribution"), Fraction())
    receipts = sum((Fraction(event["amount"]) for event in events if event["kind"] == "distribution"), Fraction())
    return contributions, receipts


def reconcile_calendar(events, dates, story, snapshot, factor):
    saved = story["dated_net_flows"]
    rows = snapshot["date_rows"]
    by_date = defaultdict(list)
    for event in events:
        by_date[event["date"]].append(event)
    require(len(dates) == len(set(dates)) == len(rows) == len(saved) == 10
            and dates == sorted(dates) and by_date.keys() <= set(dates), "Equity calendar differs")
    result = []
    for date, row, reported in zip(dates, rows, saved):
        events_on_date = by_date[date]
        contributed, received = totals(events_on_date)
        net = received - contributed
        ids = [event["event_id"] for event in events_on_date]
        require(date == row["date"] == reported["date"] and ids == row["event_ids"]
                and row["event_count"] == len(ids) and row["no_equity_event_on_declared_grid_date"] is (not ids)
                and amount(reported["net"]) == net, f"Dated equity cash differs: {date}")
        verify_amounts(row, dict(gross_contributions=contributed, gross_distributions=received, net_cash=net), date)
        result.append(dict(date=date, event_ids=ids, gross_contributions=str(contributed),
                           gross_distributions=str(received), net=str(net), normalized_net=str(net * factor)))
    return result


def reconcile_aggregates(events, story, snapshot, factor):
    category_totals = dict.fromkeys(CATEGORIES, Fraction())
    by_year = defaultdict(list)
    archived = {(row["group_kind"], row["group_key"]): row for row in snapshot["aggregate_rows"]}
    require(len(archived) == len(snapshot["aggregate_rows"]) == 13, "Expected thirteen equity aggregates")
    for event in events:
        category_totals[event["category"]] += Fraction(event["amount"])
        by_year[int(event["date"][:4])].append(event)
    require(story["cash_by_category"].keys() == category_totals.keys(), "Equity categories differ")
    verify_amounts(story["cash_by_category"], category_totals, "Saved equity categories")
    for category, value in category_totals.items():
        verify_amounts(archived.pop(("category", category))["calculated"], {"amount": value}, category)

    annual = indexed(story["annual_cash_receipts"], "calendar_cash_receipt_year")
    require(annual.keys() == by_year.keys(), "Calendar-year cash groups differ")
    output_annual = []
    for year in sorted(by_year):
        group = by_year[year]
        contributed, received = totals(group)
        operating = sum((Fraction(event["amount"]) for event in group
                         if event["category"] == "operating_distribution"), Fraction())
        amounts = dict(gross_contributions=contributed, gross_distributions=received, net_equity_cash=received - contributed,
                       operating_distributions_only=operating, normalized_operating_distributions=operating * factor)
        row = annual[year]
        require(row["conditional_coc"] is row["declared_capital_base"] is None
                and row["operating_year_coverage_financially_verified"] is False, "Annual CoC must remain pending")
        verify_amounts(row, amounts, str(year))
        verify_amounts(archived.pop(("calendar_year", str(year)))["calculated"], amounts, str(year))
        output_annual.append(dict(year=year, **{key: str(value) for key, value in amounts.items()}, conditional_coc=None))

    contributed, received = totals(events)
    require(contributed > 0, "Positive gross equity required")
    metrics = dict(gross_contributions=contributed, gross_distributions=received, net_cash_profit=received - contributed,
                   equity_multiple=received / contributed)
    verify_amounts(story, metrics, "Saved project equity metrics")
    for key, value in metrics.items():
        verify_amounts(archived.pop(("whole_horizon", key))["calculated"], {"amount": value}, key)
    require(not archived, "Unmatched archived equity aggregate")
    return metrics, category_totals, output_annual


def normalization(events, investor, story, snapshot):
    spec = investor["normalization"]
    normalized = story["normalized_story"]
    basis_ids = spec["contribution_event_ids"]
    contributions = [event for event in events if event["kind"] == "contribution"]
    basis, _ = totals(contributions)
    reference = amount(spec["reference_amount"])
    require(basis > 0 and reference > 0 and spec["basis_ref"] == normalized["basis_ref"]
            and len(basis_ids) == len(contributions) and set(basis_ids) == {event["event_id"] for event in contributions}
            and basis_ids == normalized["basis_event_ids"] == snapshot["normalization"]["basis_event_ids"],
            "Project equity normalization basis differs")
    factor = reference / basis
    scale = dict(basis_amount=basis, reference_amount=reference, scale_factor=factor)
    verify_amounts(normalized, scale, "Saved normalization")
    verify_amounts(snapshot["normalization"], scale, "D16 normalization")
    archived = indexed(snapshot["event_rows"], "event_id")
    scaled_events = indexed(normalized["events"], "event_id")
    require(scaled_events.keys() == archived.keys(), "Normalized event inventory differs")
    for event in events:
        event_id = event["event_id"]
        saved = scaled_events[event_id]
        scaled = Fraction(event["amount"]) * factor
        require(all(saved[key] == event[key] for key in EVENT_FIELDS)
                and amount(saved["amount"]) == scaled == amount(archived[event_id]["normalized_amount"]),
                f"Normalized equity event differs: {event_id}")
        event["normalized_amount"] = str(scaled)
    return factor, scale


def reconcile_snapshot(root, snapshot, cash):
    input_ref = snapshot["input_ref"]
    require(input_ref == cash["input_ref"] and snapshot["result_ref"] == cash["result_ref"],
            "Return source or result differs from lifecycle replay")
    case = resolve(root, input_ref | {"embedded_json_pointers": CASE_CHAIN})
    saved = resolve(root, snapshot["result_ref"])
    story = saved["current_project_return_story"]
    investor_raw = case["investor_source_utf8"]
    investor = json.loads(investor_raw)
    binding = json.loads(case["return_binding_source_utf8"])
    compiled = json.loads(saved["current_compiled_investor_json"])
    require(digest(investor_raw) == binding["investor_source_sha256"]
            and investor["context"] == story["context"] == saved["context"] == snapshot["context"]
            and investor["currency"] == story["currency"] == snapshot["currency"] == "USD"
            and investor["equity_level"] == story["equity_level"] == snapshot["equity_level"] == "aggregate_project_equity"
            and investor["event_inventory_declared_complete"] is True, "Unexpected project equity source")
    require(saved["decision"] == snapshot["financial_decision"] == "PENDING"
            and saved["personal_investor_return"] is None and story["selected_IRR"] is None
            and not any((investor["capital_snapshots"], investor["annual_cash_bases"], story["capital_snapshots"])),
            "Unexpected investor decision, rate selection or capital basis")
    events = reconcile_events(cash["events"], investor, binding, compiled, story, snapshot)
    factor, scale = normalization(events, investor, story, snapshot)
    dates = investor["grid"]["dates"]
    require(story["cash_horizon"] == snapshot["cash_horizon"] ==
            dict(start=dates[0], end=dates[-1], future_cash_after_horizon_included=False), "Cash horizon differs")
    calendar = reconcile_calendar(events, dates, story, snapshot, factor)
    metrics, categories, annual = reconcile_aggregates(events, story, snapshot, factor)
    scaled_totals = dict(total_contributions=metrics["gross_contributions"] * factor,
                         total_distributions=metrics["gross_distributions"] * factor,
                         net_cash_profit=metrics["net_cash_profit"] * factor, equity_multiple=metrics["equity_multiple"])
    verify_amounts(story["normalized_story"], scaled_totals, "Normalized project equity totals")
    result = dict(snapshot=snapshot["snapshot_id"], equity_level="aggregate_project_equity",
                  events=events, calendar=calendar, calendar_year_cash=annual,
                  cash_by_category={key: str(categories[key]) for key in sorted(categories)},
                  **{key: str(value) for key, value in metrics.items()},
                  normalized={key: str(value) for key, value in (scale | scaled_totals).items()},
                  capital_still_invested=None, retained_equity_value=None, personal_investor_return=None)
    return result, (compiled, story, saved["current_irr_evidence"])


def replay_with_sources(root=ROOT):
    lifecycle = replay_lifecycle(root, include_return_cash=True)
    register = json.loads(local_file(root, REGISTER).read_bytes())
    snapshots = register["snapshots"]
    require(register["snapshot_id"] == "D16" and [row["snapshot_id"] for row in snapshots] == ["L01", "L02"],
            "Expected both D16 equity snapshots")
    by_path = indexed([dict(row, path=row["input_ref"]["path"]) for row in snapshots], "path")
    sources = []
    for case in lifecycle["snapshots"]:
        cash = case.pop("return_cash")
        snapshot = by_path.pop(cash["input_ref"]["path"])
        case["project_equity"], evidence = reconcile_snapshot(root, snapshot, cash)
        sources.append(evidence)
    require(not by_path, "Unmatched project equity snapshot")
    return lifecycle, sources


def run(root=ROOT):
    report, _ = replay_with_sources(root)
    return report


if __name__ == "__main__":
    try:
        print(json.dumps(run(), ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
