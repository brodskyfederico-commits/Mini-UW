"""Rebuild synthetic refinance, operating debt and sale for four declared sensitivities."""
from argparse import ArgumentParser
from dataclasses import replace
from fractions import Fraction
from hashlib import sha256
import json
import sys

from check_integrated_participation_D28 import allocate, ledger, replay_with_ledgers
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_participant_funding_risk_D29 import observe_allocation
from check_return_replay_D23 import indexed
from demo_project_sale_revisions import load_evidence
from miniuw_foundation.capacity_project_returns import assemble_capacity_checked_returns
from miniuw_foundation.closing_cash import produce_closing_cash
from miniuw_foundation.debt_closing import reconcile_debt_closing
from miniuw_foundation.debt_service import produce_debt_service, rational
from miniuw_foundation.drafts import canonical, digest
from miniuw_foundation.operating_cash import reconcile_operating_cash
from miniuw_foundation.project_cash import reconcile_project_cash
from miniuw_foundation.project_sale_revision import evidence_fingerprint
from miniuw_foundation.refinance_capacity import size_refinance


FIXTURE = "templates/synthetic-participant-refinance-variants-D31.json"
SCHEMA = "miniuw.synthetic-participant-refinance-sensitivity.v1"
CAPACITY_BLOCKER = "selected_principal_exceeds_declared_bank_capacity"


def encode(value):
    return canonical(value).encode("utf-8")


def set_claim(claim, value, provenance):
    claim.update(value=rational(value), source_ref=provenance)


def rebind_closing(prior, source, loans):
    raw = encode(source)
    closing = produce_closing_cash(raw)
    binding = json.loads(prior.debt_spec_raw)
    binding.update(closing_source_sha256=sha256(raw).hexdigest(), closing_run_sha256=closing.sha256)
    for row, loan in zip(binding["loans"], loans, strict=True):
        row.update(loan_source_sha256=sha256(loan.loan_raw).hexdigest(), loan_run_sha256=loan.run.sha256)
    binding_raw = encode(binding)
    debt = reconcile_debt_closing(loans, raw, closing, binding_raw)
    require(closing.payload["state"] == "computed_synthetic_closing"
            and debt.payload["state"] == "matched_synthetic_debt_assumptions", f"Unreconciled closing: {prior.closing_id}")
    return replace(prior, closing_raw=raw, closing_run=closing, loans=loans, debt_spec_raw=binding_raw, debt_run=debt)


def rebuild_cash(base, spec):
    pre, post = base.periods
    original_refi, original_sale = base.closings
    principal = amount(spec["selected_principal"])
    cost = amount(spec["refinance_closing_costs"])
    provenance = spec["variant_id"]
    require(principal > 0 and cost >= 0, "Positive principal and nonnegative costs required")

    original_loan, = original_sale.loans
    terms = json.loads(original_loan.loan_raw)
    terms["principal"] = rational(principal)
    loan_raw = encode(terms)
    loan = replace(original_loan, loan_raw=loan_raw, run=produce_debt_service(loan_raw, original_loan.windows))

    refi = json.loads(original_refi.closing_raw)
    set_claim(refi["amounts"]["gross_proceeds"], principal, provenance)
    set_claim(refi["new_loan"]["principal_after_closing"], principal, provenance)
    set_claim(refi["amounts"]["closing_costs_paid"], cost, provenance)
    refi["equity_funding_assumption_ref"] = spec["equity_funding_assumption_ref"]
    refinance = rebind_closing(original_refi, refi, original_refi.loans)

    operating = json.loads(post.spec_raw)
    sale = json.loads(original_sale.closing_raw)
    cut = sale["closing_date"]
    require(operating["start_date"] == refi["closing_date"] and operating["end_date"] == cut,
            "Refinance to sale dates differ")
    schedule = loan.run.payload["schedule"]
    payments = [row for row in schedule if operating["start_date"] <= row["date"] < cut]
    sale_payment, = [row for row in schedule if row["date"] == cut]
    claims = operating["amounts"]
    free = amount(claims["closing_free_cash_claim"])
    for field, schedule_field in (("debt_principal_payment", "principal_due"), ("debt_interest_payment", "interest_due")):
        value = sum((amount(row[schedule_field]) for row in payments), Fraction())
        free += amount(claims[field]) - value
        set_claim(claims[field], value, provenance)
    set_claim(claims["closing_free_cash_claim"], free, provenance)
    operating_raw = encode(operating)
    cash = reconcile_operating_cash(post.noi_raw, post.noi_run, operating_raw)
    require(not cash.payload["blockers"] and amount(cash.payload["total_cash_conservation_residual"]) == 0, "Revised operating cash did not reconcile")
    periods = (pre, replace(post, spec_raw=operating_raw, cash_run=cash))

    set_claim(sale["amounts"]["opening_free_cash"], free, provenance)
    debt, = sale["old_debts"]
    for field, schedule_field in (("principal", "opening_balance"), ("interest", "interest_due")):
        for suffix in ("due", "paid"):
            set_claim(debt[f"{field}_{suffix}"], amount(sale_payment[schedule_field]), provenance)
    closing = rebind_closing(original_sale, sale, (loan,))
    require(amount(claims["debt_principal_payment"]) + amount(debt["principal_paid"]) == principal,
            "New principal failed to reconcile from draw to sale")
    return periods, (refinance, closing), loan


def reconcile_variant(base, spec):
    periods, closings, loan = rebuild_cash(base, spec)
    pre, post = periods
    refinance, sale = closings
    manifest = json.loads(base.manifest_raw)
    nodes = indexed(manifest["nodes"], "node_id")
    for closing in closings:
        nodes[closing.closing_id].update(
            source_sha256=sha256(closing.closing_raw).hexdigest(), run_sha256=closing.closing_run.sha256,
            upstream_source_sha256=sha256(closing.debt_spec_raw).hexdigest(), upstream_run_sha256=closing.debt_run.sha256)
    node = nodes[post.cash_run.payload["period_ref"]]
    node.update(source_sha256=sha256(post.spec_raw).hexdigest(), run_sha256=post.cash_run.sha256)
    manifest_raw = encode(manifest)
    project = reconcile_project_cash(periods, closings, manifest_raw)
    require(project.payload["declared_cash_window_reconciled"]
            and amount(project.payload["cash_conservation_residual"]) == 0, "Revised project cash did not reconcile")

    inputs = replace(base.capacity_inputs, new_loan=loan, closing_raw=refinance.closing_raw,
                     closing_run=refinance.closing_run)
    capacity_spec = json.loads(base.capacity_spec_raw)
    set_claim(capacity_spec["selected_principal"], amount(spec["selected_principal"]), spec["variant_id"])
    capacity_spec.update(new_loan_source_sha256=sha256(loan.loan_raw).hexdigest(), new_loan_run_sha256=loan.run.sha256,
                         closing_source_sha256=sha256(refinance.closing_raw).hexdigest(),
                         closing_run_sha256=refinance.closing_run.sha256)
    capacity_raw = encode(capacity_spec)
    capacity = size_refinance(inputs, capacity_raw)

    investor = json.loads(base.investor_raw)
    cash_in_id = "refinance-cash-in"
    investor["events"].append(dict(event_id=cash_in_id, date=refinance.closing_run.payload["closing_date"],
                                   kind="contribution", category="refinance_cash_in", amount=None, currency="USD",
                                   source_ref=None))
    investor["normalization"]["contribution_event_ids"].append(cash_in_id)
    investor_raw = encode(investor)
    inner = base.binding.project_return_binding
    slots = tuple(replace(slot, contribution_event_id=cash_in_id) if slot.node_id == refinance.closing_id else slot
                  for slot in inner.slots)
    inner = replace(inner, manifest_source_sha256=sha256(manifest_raw).hexdigest(), project_run_sha256=project.sha256,
                    investor_source_sha256=sha256(investor_raw).hexdigest(), slots=slots)
    binding = replace(base.binding, capacity_spec_sha256=sha256(capacity_raw).hexdigest(), capacity_run_sha256=capacity.sha256,
                      project_return_binding=inner)
    guarded = assemble_capacity_checked_returns(periods, closings, manifest_raw, project, inputs,
                                                 capacity_raw, capacity, investor_raw, binding)
    return capacity, guarded, refinance, sale, post


def replay_variants(fixture, base):
    require(fixture["schema"] == SCHEMA and fixture["base_evidence_sha256"] == evidence_fingerprint(base)
            and fixture["fixed_sources_basis_ref"], "Refinance sensitivity basis differs")
    original_maximum = amount(base.capacity_run.payload["maximum_principal_capacity"])
    variants = {}
    for key, spec in indexed(fixture["variants"], "variant_id").items():
        capacity, guarded, refinance, sale, post = reconcile_variant(base, spec)
        sizing = capacity.payload
        selected = amount(sizing["selected_principal"])
        maximum = amount(sizing["maximum_principal_capacity"])
        require(selected == amount(spec["selected_principal"]) and maximum == original_maximum
                and sizing["bank_credit_approved"] is sizing["funds_available_verified"] is False
                and sizing["decision"] == guarded.payload["decision"] == "PENDING", "Refinance sizing scope differs")
        post_amounts = json.loads(post.spec_raw)["amounts"]
        sale_debt = json.loads(sale.closing_raw)["old_debts"][0]
        row = dict(selected_principal=str(selected), capacity=str(maximum), capacity_blockers=sizing["blockers"],
                   refinance_closing_costs=str(amount(spec["refinance_closing_costs"])),
                   operating_principal=str(amount(post_amounts["debt_principal_payment"])),
                   operating_interest=str(amount(post_amounts["debt_interest_payment"])),
                   sale_payoff_principal=str(amount(sale_debt["principal_paid"])), project=None, participants=None)
        parent = None
        if selected > maximum:
            require(sizing["blockers"] == [CAPACITY_BLOCKER] and guarded.compiled_raw is guarded.investor_run is None
                    and "refinance_capacity_or_selection_blocked" in guarded.payload["blockers"],
                    "Above-capacity variant leaked a return")
        else:
            require(not sizing["blockers"] and guarded.compiled_raw is not None, "Within-capacity variant failed")
            story = guarded.investor_run.payload
            totals = story["cash_by_category"]
            for category, producer, field in (
                ("net_refinance_distribution", refinance, "exportable_equity_distribution"),
                ("refinance_cash_in", refinance, "exportable_equity_contribution"),
                ("net_sale_distribution", sale, "exportable_equity_distribution"),
            ):
                require(totals[category] == producer.closing_run.payload[field], f"Gross cash category differs: {category}")
            parent = ledger(story, json.loads(guarded.compiled_raw)) | {"guarded_run_sha256": guarded.sha256}
        variants[key] = (row, parent)
    return variants


def participant_rows(risk, allocation, fields):
    return [
        dict(participant_id=part["participant_id"], share_fraction=part["share_fraction"],
             metrics={field: part["metrics"][field] for field in fields},
             refinance_distribution=cash["cash_by_category"]["net_refinance_distribution"],
             operating_distribution=cash["cash_by_category"]["operating_distribution"],
             dated_events=cash["dated_events"], irr_root_classification=cash["periodic_IRR"]["root_classification"])
        for part, cash in zip(risk["participants"], allocation["participants"], strict=True)
    ]


def run():
    base, ledgers, terms = replay_with_ledgers()
    fixture = json.loads(local_file(ROOT, FIXTURE).read_bytes())
    require(fixture["allocation_terms_sha256"] == base["terms_sha256"], "Refinance participation terms differ")
    reference_evidence = load_evidence(independent_test_fixture=True)
    cases = replay_variants(fixture, reference_evidence)
    hashes = fixture["project_ledgers"]
    require(hashes.keys() == {key for key, (_, parent) in cases.items() if parent is not None},
            "Unexpected refinance ledger bindings")
    baseline_allocation = base["scenarios"]["refinance_independent_fixture"]
    baseline_ledger = ledgers["refinance_independent_fixture"]
    baseline = observe_allocation(baseline_allocation, baseline_ledger)
    fields = ("gross_contributions", "gross_distributions", "net_cash_profit",
              "refinance_cash_in_contributions", "net_sale_distribution", "cash_shortfall_at_horizon",
              "peak_cumulative_net_equity_funding_at_date_close", "possible_intraday_peak_upper_bound",
              "sale_share_of_distributions")
    reference = dict(selected_principal=str(amount(reference_evidence.capacity_run.payload["selected_principal"])),
                     participants=participant_rows(baseline, baseline_allocation, fields))
    reports = {}
    for key, (row, parent) in cases.items():
        allocated = allocate(terms, parent, hashes.get(key), require_unique_irr=False)
        risk = observe_allocation(allocated, parent)
        row["state"] = risk["state"]
        if parent is not None:
            require(risk["project"] is not None and risk["cash_horizon"] == baseline["cash_horizon"],
                    f"Revised cash failed to allocate: {key}")
            unchanged = {"initial_capital", "operating_distribution"}
            require(parent["evidence"]["grid"] == baseline_ledger["evidence"]["grid"]
                    and parent["evidence"]["parameters"] == baseline_ledger["evidence"]["parameters"],
                    "Refinance variant changed the calendar or IRR controls")
            original_events = indexed(baseline_ledger["story"]["dated_events"], "event_id")
            for event in parent["story"]["dated_events"]:
                if event["category"] in unchanged:
                    require(all(event[key] == original_events[event["event_id"]][key]
                                for key in ("amount", "date", "kind", "category", "currency")),
                            "Refinance variant changed initial or operating equity cash")
            row["project"] = {field: risk["project"]["metrics"][field] for field in fields}
            row["participants"] = participant_rows(risk, allocated, fields)
        reports[key] = row
    return dict(status="passed", scope="synthetic_refinance_sensitivity", currency="USD", decision="PENDING",
                allocation_terms_sha256=base["terms_sha256"], reference=reference, variants=reports,
                verified_personal_investor_return=None, deployment_enabled=False, real_decisions_enabled=False)


def summary(report):
    return dict(status=report["status"], decision=report["decision"], refinance_variant_sha256=digest(canonical(report)),
                variant_states={key: row["state"] for key, row in report["variants"].items()})


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--summary", action="store_true", help="Print variant states and the full report SHA-256.")
    args = parser.parse_args()
    try:
        report = run()
        print(json.dumps(summary(report) if args.summary else report, ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
