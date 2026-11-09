"""Carry the exact D38 capacity decision into dated synthetic participant returns."""
from argparse import ArgumentParser
from fractions import Fraction
import json
import sys

from check_integrated_participation_D28 import TERMS, allocate, ledger
from check_joint_noi_capacity_D38 import FIXTURE as MATRIX, replay_with_cash
from check_operating_replay_D20 import ROOT, local_file, require
from check_participant_funding_risk_D29 import observe_allocation
from check_participant_refinance_variants_D31 import CAPACITY_BLOCKER, participant_rows
from miniuw_foundation.drafts import canonical, digest


BINDINGS = "templates/synthetic-joint-noi-investor-returns-D39.json"
SCHEMA = "miniuw.synthetic-joint-noi-investor-returns.v1"
FIELDS = ("gross_contributions", "gross_distributions", "net_cash_profit",
          "refinance_cash_in_contributions", "net_sale_distribution", "cash_shortfall_at_horizon",
          "peak_cumulative_net_equity_funding_at_date_close", "sale_share_of_distributions")


def cases_from_cash(matrix, guarded_by_case):
    for row in matrix["matrix"]:
        for key, loan in row["loans"].items():
            case = f"{row['bank_noi']}/{row['valuation_noi']}/{key}"
            guarded = guarded_by_case[case]
            require(guarded.payload["decision"] == "PENDING" and guarded.payload["production_authorized"] is False,
                    "Matrix case acquired a decision or authorization")
            principal = Fraction(loan["principal"])
            exceeded = [label for label, field in (("DSCR", "dscr_capacity"), ("LTV", "ltv_capacity"))
                        if principal > Fraction(loan[field])]
            parent = None
            if exceeded:
                require(loan["state"] == "PENDING" and loan["blockers"] == [CAPACITY_BLOCKER]
                        and guarded.compiled_raw is guarded.investor_run is None
                        and "refinance_capacity_or_selection_blocked" in guarded.payload["blockers"],
                        "Blocked loan exposed current investor cash")
            else:
                require(loan["state"] == "compatible_synthetic_capacity" and not loan["blockers"]
                        and guarded.compiled_raw is not None, "Compatible loan lost investor cash")
                parent = ledger(guarded.investor_run.payload, json.loads(guarded.compiled_raw))
                parent["guarded_run_sha256"] = guarded.sha256
            result = dict(bank_noi=row["bank_noi"], valuation_noi=row["valuation_noi"], loan_variant=key,
                          principal=loan["principal"], capacity=loan["capacity"], binding_limits=row["binding_limits"],
                          exceeded_limits=exceeded, blockers=loan["blockers"], decision="PENDING",
                          return_state="PENDING", participants=None, project=None)
            yield case, result, parent


def replay_cases():
    return cases_from_cash(*replay_with_cash())


def expose_returns(terms, parent, binding):
    allocation = allocate(terms, parent, binding)
    risk = observe_allocation(allocation, parent)
    require(risk["project"] is not None, "Compatible scenario did not reconcile its participant returns")
    participants = participant_rows(risk, allocation, FIELDS)
    for row, allocated in zip(participants, allocation["participants"], strict=True):
        row.update(equity_multiple=allocated["equity_multiple"], annual_irr_roots=allocated["annual_IRR_roots"],
                   selected_irr=None)
    return dict(return_state="computed_synthetic_cash_allocation", participants=participants,
                project={key: risk["project"]["metrics"][key] for key in FIELDS})


def run():
    terms_raw = local_file(ROOT, TERMS).read_text(encoding="utf-8")
    matrix_raw = local_file(ROOT, MATRIX).read_text(encoding="utf-8")
    bindings = json.loads(local_file(ROOT, BINDINGS).read_bytes())
    require(bindings["schema"] == SCHEMA and bindings["allocation_terms_sha256"] == digest(terms_raw)
            and bindings["matrix_fixture_sha256"] == digest(matrix_raw), "Joint NOI return sources differ")
    terms = json.loads(terms_raw)
    pending_bindings = dict(bindings["project_ledgers"])
    cases = {}
    for case, row, parent in replay_cases():
        if parent is not None:
            row.update(expose_returns(terms, parent, pending_bindings.pop(case)))
        cases[case] = row
    require(not pending_bindings and len(cases) == 24, "Unexpected return binding inventory")
    return dict(status="passed", scope="synthetic_joint_noi_and_investor_cash", currency="USD", decision="PENDING",
                scenarios=cases, verified_personal_investor_return=None,
                deployment_enabled=False, real_decisions_enabled=False)


def summary(report):
    states = [row["return_state"] for row in report["scenarios"].values()]
    return dict(status=report["status"], decision=report["decision"], joint_noi_returns_sha256=digest(canonical(report)),
                computed=states.count("computed_synthetic_cash_allocation"), pending=states.count("PENDING"))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--summary", action="store_true", help="Print scenario counts and the full report SHA-256.")
    args = parser.parse_args()
    try:
        report = run()
        print(json.dumps(summary(report) if args.summary else report, ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
