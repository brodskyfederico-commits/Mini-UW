"""Cross the declared bank and valuation NOI sources and replay both capacity gates."""
from argparse import ArgumentParser
from fractions import Fraction
import json
import sys

from check_bank_noi_capacity_order_D36 import FIXTURE as BANK
from check_discount_rate_crossover_D35 import HIGH, LOW
from check_ltv_capacity_order_D37 import FIXTURE as VALUATION, observe, replay_valuation
from check_operating_replay_D20 import ROOT, amount, local_file, require
from check_participant_refinance_variants_D31 import CAPACITY_BLOCKER, FIXTURE as REFINANCE, build_variant_evidence
from check_return_replay_D23 import indexed
from demo_project_sale_revisions import load_evidence
from miniuw_foundation.drafts import canonical, digest
from miniuw_foundation.project_sale_revision import evidence_fingerprint


FIXTURE = "templates/synthetic-joint-noi-capacity-D38.json"
SCHEMA = "miniuw.synthetic-joint-noi-capacity.v1"


def read_bound(path, expected):
    raw = local_file(ROOT, path).read_text(encoding="utf-8")
    require(digest(raw) == expected, f"Joint NOI source differs: {path}")
    return json.loads(raw)


def replay_with_cash():
    """Return the unchanged capacity report and the guarded cash for each matrix loan."""
    fixture = json.loads(local_file(ROOT, FIXTURE).read_bytes())
    require(fixture["schema"] == SCHEMA and fixture["joint_basis_ref"], "Expected declared joint NOI fixture")
    bank = read_bound(BANK, fixture["bank_fixture_sha256"])
    valuation = read_bound(VALUATION, fixture["valuation_fixture_sha256"])
    refinance = read_bound(REFINANCE, fixture["refinance_fixture_sha256"])
    require(valuation["bank_fixture_sha256"] == fixture["bank_fixture_sha256"], "Valuation fixture binds other bank evidence")
    bank_levels = [amount(v) for v in bank["bank_noi_scenarios"]]
    valuation_levels = [amount(v) for v in valuation["valuation_noi_scenarios"]]
    require(bank_levels == [750, 1500, 2000] and valuation_levels == [15, 30, 49, 50],
            "Expected all declared NOI levels")

    reference = load_evidence(independent_test_fixture=True)
    require(evidence_fingerprint(reference) == refinance["base_evidence_sha256"], "Refinance base evidence differs")
    variants = indexed(refinance["variants"], "variant_id")
    parents = {key: build_variant_evidence(reference, variants[key]) for key in (LOW, HIGH)}
    spec = json.loads(reference.capacity_spec_raw)["parameters"]
    dscr_factor = amount(spec["minimum_dscr"]) * amount(reference.capacity_run.payload["regular_annual_sizing_constant"])
    ltv_factor = amount(spec["maximum_ltv"]) / amount(spec["cap_rate"])

    matrix = []
    ties = []
    guarded_by_case = {}
    for bank_noi in bank_levels:
        dscr_cap = bank_noi / dscr_factor
        for valuation_noi in valuation_levels:
            ltv_cap = valuation_noi * ltv_factor
            maximum = min(dscr_cap, ltv_cap)
            source = f"SYNTHETIC-D38/{bank_noi}/{valuation_noi}"
            results = {}
            for key, parent in parents.items():
                result, guarded = replay_valuation(parent, valuation_noi, source, bank_noi=bank_noi)
                results[key] = result
                guarded_by_case[f"{bank_noi}/{valuation_noi}/{key}"] = guarded
            for result in results.values():
                blocked = Fraction(result["principal"]) > maximum
                require(Fraction(result["capacity"]) == maximum
                        and Fraction(result["dscr_capacity"]) == dscr_cap
                        and Fraction(result["ltv_capacity"]) == ltv_cap
                        and result["blockers"] == ([CAPACITY_BLOCKER] if blocked else [])
                        and (result["state"] == "PENDING") == blocked, "Joint NOI capacity or selected loan state differs")
            matrix.append(dict(bank_noi=str(bank_noi), valuation_noi=str(valuation_noi),
                               capacity=str(maximum), binding_limits=results[LOW]["binding_limits"], loans=results))

        exact_tie = dscr_cap / ltv_factor
        tie_probes = {}
        for label, offset, limits in (("below", Fraction(-1, 100), ["LTV"]),
                                      ("at", 0, ["DSCR", "LTV"]),
                                      ("above", Fraction(1, 100), ["DSCR"])):
            probe = observe(parents[LOW], exact_tie + offset, f"SYNTHETIC-D38/{bank_noi}/tie/{label}", bank_noi=bank_noi)
            require(probe["binding_limits"] == limits
                    and (Fraction(probe["ltv_capacity"]) == Fraction(probe["dscr_capacity"])) == (offset == 0),
                    "Joint NOI tie differs")
            tie_probes[label] = probe
        ties.append(dict(bank_noi=str(bank_noi), exact_valuation_noi=str(exact_tie), probes=tie_probes))
    report = dict(status="passed", scope="synthetic_joint_bank_and_valuation_noi", currency="USD", decision="PENDING",
                  matrix=matrix, ties=ties, deployment_enabled=False, real_decisions_enabled=False)
    return report, guarded_by_case


def run():
    report, _ = replay_with_cash()
    return report


def summary(report):
    return dict(status=report["status"], decision=report["decision"], joint_noi_capacity_sha256=digest(canonical(report)),
                combinations=len(report["matrix"]),
                blocked_loans=sum(loan["state"] == "PENDING" for row in report["matrix"] for loan in row["loans"].values()),
                tie_probes=sum(len(tie["probes"]) for tie in report["ties"]))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--summary", action="store_true", help="Print verification counts and the full report SHA-256.")
    args = parser.parse_args()
    try:
        report = run()
        print(json.dumps(summary(report) if args.summary else report, ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
