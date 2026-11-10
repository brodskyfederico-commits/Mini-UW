"""Check initial USD 10, separate later contributions, and reject wrong denominators."""
from argparse import ArgumentParser
from fractions import Fraction
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

from pypdf import PdfReader

from check_investor_answers_D77 import INDEX, answers, report_cash, verified_reports
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_pending_investor_answers_D78 import CASES, settled_variant, worksheet_variant
from check_reference_package import PackageError
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_linked_cotejo_D54 import publish
from reissue_investor_reports_D76 import FIXTURE, normalize
from worksheet_investor_D74 import display


def initial_flows(events):
    return [e for e in events if e["kind"] == "contribution" and e["category"] == "initial_capital"]


def verify_basis(cash):
    events = cash["events"]
    initial = initial_flows(events)
    extra = [e for e in events if e["kind"] == "contribution" and e["category"] != "initial_capital"]
    total = amount(cash.get("contributions", cash.get("gross_contributions")))
    require(initial and sum(amount(e["amount"]) for e in initial) == 10
            and sum(amount(e["amount"]) for e in extra) == total - 10,
            "USD 10 must be initial equity with all later contributions kept separate")
    require(sum(Fraction(display(e["amount"])) for e in initial) == 10,
            "Rounded initial amounts on the page do not add to USD 10")
    return dict(initial_equity=rational(Fraction(10)), initial_events=initial,
                extra_equity=rational(total - 10), total_equity=rational(total))


def verify_reports():
    archive, _ = verified_reports()
    rows = {}
    with ZipFile(BytesIO(archive)) as package:
        reports = json.loads(package.read(INDEX))["reports"]
        for name, report in reports.items():
            page, = PdfReader(BytesIO(package.read(name + ".pdf"))).pages
            text = page.extract_text()
            rows[name] = {}
            for label, cash in report_cash(report).items():
                expected = report["verified_answers_per_usd_10"][label]
                if cash is None:
                    require(expected is None and report["state"] == "PENDING"
                            and "Cuanto cobro: PENDIENTE." in text and "Aporte inicial |" not in text,
                            "A pending report displayed an initial contribution as verified")
                    rows[name][label] = None
                    continue
                basis = verify_basis(cash)
                require(amount(expected["initial_equity"]) == 10
                        and expected["extra_contributions"] == basis["extra_equity"],
                        "The four-answer record differs from its dated contributions")
                by_date = {}
                for event in basis["initial_events"]:
                    when = event["date"]
                    by_date[when] = by_date.get(when, 0) + amount(event["amount"])
                for when, value in by_date.items():
                    prefix = f"{label} " if label else ""
                    shown = f"{prefix}{'-' if value else ''}USD {display(rational(value))}"
                    require(any(line.startswith(f"{when}  Aporte inicial |") and shown in line
                                for line in text.splitlines()),
                            "The PDF did not show the dated initial USD contribution")
                rows[name][label] = basis
    return rows, sha(archive)


def verify_variants():
    delivered = json.loads(local_file(ROOT, FIXTURE).read_bytes())["delivered"]
    by_name = {row["id"]: row for row in delivered}
    cache = {}
    rows = {}
    control_story = None
    for name, _, _, control, replacement in CASES:
        key = (control, replacement)
        if key not in cache:
            story, source = (worksheet_variant(by_name[name], replacement) if control == "worksheet"
                             else settled_variant(control, replacement))
            cash = normalize(story)
            basis = verify_basis(cash)
            original = initial_flows(story.get("dated_events", story.get("events")))
            original_base = sum(amount(e["amount"]) for e in original)
            source_schedule = [(e["date"], amount(e["amount"]) * 10 / original_base)
                               for e in sorted(original, key=lambda e: e["date"])]
            require(source_schedule == [(e["date"], amount(e["amount"])) for e in basis["initial_events"]],
                    "Initial events do not reflect the verified archived initial source")
            cache[key] = basis | dict(source=source, source_initial_equity=rational(original_base))
            if amount(basis["extra_equity"]) > 0:
                control_story = story
        rows[name] = cache[key]
    return rows, control_story


def verify_negative_controls(story):
    key = "dated_events" if "dated_events" in story else "events"
    events = story[key]
    cash = normalize(story)
    total = amount(cash["contributions"])
    require(total > 10, "The denominator control requires a later contribution")
    factor = Fraction(10) / total
    wrong_events = [event | {"amount": rational(amount(event["amount"]) * factor)} for event in cash["events"]]
    wrong = cash | {"events": wrong_events,
                    **{key: rational(amount(cash[key]) * factor)
                       for key in ("contributions", "distributions", "net_cash", "unrecovered_at_cutoff")}}
    try:
        answers(wrong)
    except PackageError as error:
        require("do not reconcile" in str(error), "Wrong denominator failed for an unexpected reason")
    else:
        raise AssertionError("USD 10 total contributions were accepted in place of USD 10 initial")
    missing_initial = [e | {"category": "additional_capital"} if e in initial_flows(events) else e for e in events]
    require(normalize(story | {key: missing_initial}) is None,
            "A missing initial contribution fell back to a different denominator")


def verify():
    reports, source_sha256 = verify_reports()
    variants, control_story = verify_variants()
    calculated = [value for cases in reports.values() for value in cases.values() if value is not None]
    pending = {name for name, cases in reports.items() if all(value is None for value in cases.values())}
    require(len(reports) == 40 and len(calculated) == 33 and len(pending) == 8
            and pending == variants.keys(), "Unexpected report or synthetic variant scope")
    verify_negative_controls(control_story)
    return dict(status="passed", decision="PENDING", synthetic_only=True, reports_checked=len(reports),
                original_scenarios_with_exact_initial_usd_10=len(calculated), original_reports_pending=len(pending),
                separate_variants_with_exact_initial_usd_10=len(variants), wrong_total_basis_rejected=True,
                missing_initial_basis_withheld=True, d77_archive_sha256=source_sha256,
                reports=reports, separate_synthetic_variants=variants)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify()
    if args.output:
        publish(args.output, report)
    print(json.dumps({k: v for k, v in report.items() if k not in ("reports", "separate_synthetic_variants")},
                     ensure_ascii=False))
