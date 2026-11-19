"""Verify versioned exact transport, legacy isolation and the D262 precision case."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from fractions import Fraction
from importlib import import_module
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import test_worksheet_permanent_sensitivities as debt_tests
import worksheet_exact_cash_D263 as transport
from check_worksheet_technical_acceptance_D200 import settings_for_acceptance, source_files
from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.operating_noi import _bounded, ArithmeticBudgetError
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, encoded, read_case_source, read_package, verify_package
from worksheet_annual_coc import quantity as amount
from worksheet_intake_D198 import assemble, register
from worksheet_sensitivities_D253 import EXACT_PERMANENT_SCHEMA, evaluate_trial


def request(parents, inputs, *, precision=False):
    spec = debt_tests.request(parents, inputs)
    spec["schema"] = EXACT_PERMANENT_SCHEMA
    if precision:
        for name, rate in (("Base", "0.0501"), ("Downside", "0.0651")):
            case = spec["scenarios"][name]
            case["changes"][0] = debt_tests.change("C69", rate)
            case["permanent_support"]["individual"]["C69"] = debt_tests.pdf_support(
                parents[name], inputs, name, "D263-precision-C69", dict(C69=rate))
            case["permanent_support"]["combined"] = debt_tests.pdf_support(
                parents[name], inputs, name, "D263-precision-combined", debt_tests.TARGETS[name] | dict(C69=rate))
    return spec


def cash_values(cash):
    return dict(events=[{k:e[k] for k in ("event_id", "date", "kind", "amount")} for e in cash["events"]],
        totals={k:cash[k] for k in ("basis_amount", "reference_amount", "scale_factor", "total_contributions",
                                  "total_distributions", "net_cash_profit", "unrecovered_after_sale")})


class ExactCashTransportTests(TestCase):
    def test_reader_is_exact_bounded_and_never_coerces_a_blank(self):
        value = rational(Fraction(10**369+7, 10**365+9))
        self.assertEqual(transport.exact_fraction(value), Fraction(int(value["numerator"]), int(value["denominator"])))
        with self.assertRaises(ValueError):
            _fraction(value)
        with self.assertRaises(ValueError):
            transport.exact_fraction(value, 24)
        self.assertIsNone(transport.exact_fraction(None))
        self.assertEqual(transport.exact_fraction(rational(0)), 0)
        for invalid in ("", " ", {}, dict(numerator="1", denominator="0"), dict(numerator="1"*1301, denominator="1")):
            with self.assertRaises((ValueError, TypeError)):
                transport.exact_fraction(invalid)
        with self.assertRaises(ArithmeticBudgetError):
            _bounded(Fraction(2**4097))

    def test_namespaces_are_isolated_and_legacy_code_is_unchanged(self):
        modules = {name:import_module(name) for name in transport.ALGORITHMS}
        before = {name:{k:id(v) for k,v in vars(module).items()} for name,module in modules.items()}
        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = list(pool.map(lambda _:transport.cash_engine(), range(2)))
        a, b = first[0].__globals__, second[0].__globals__
        self.assertIsNot(a, b)
        self.assertIsNot(a, vars(modules["plan_refinance_D108"]))
        self.assertIs(first[0].__code__, modules["plan_refinance_D108"].financed_cash.__code__)
        self.assertEqual(first[1], second[1])
        self.assertEqual(first[1]["rounding"], "none")
        self.assertEqual(first[1]["arithmetic_max_bits"], 4096)
        self.assertEqual(a["closing_cash"].produce_closing_cash.__globals__["_fraction"], transport.exact_fraction)
        self.assertEqual(a["reconcile_year"].__globals__["operating_cash"].reconcile_operating_cash.__globals__["_fraction"], transport.exact_fraction)
        self.assertEqual(a["bind_closing"].__globals__["assemble_closing_returns"].__globals__["produce_investor_returns"].__globals__["_fraction"], transport.exact_fraction)
        self.assertEqual({name:{k:id(v) for k,v in vars(module).items()} for name,module in modules.items()}, before)
        self.assertIs(modules["plan_refinance_D108"]._fraction, _fraction)
        with patch.dict(transport.ALGORITHMS, {"plan_return_D107":"0"*64}):
            with self.assertRaisesRegex(ValueError, "algorithm_revision_unconfirmed"):
                transport.cash_engine()

    def test_unreviewed_algorithm_blocks_instead_of_falling_back(self):
        parent = dict(document_id="SYNTHETIC-D263-parent", revision="SYNTHETIC-D263-prior", source_sha256="a"*64,
            blockers=[], document={k:rational(Fraction(v)) for k,v in dict(requested_principal=1_400_000,
            annual_nominal_rate="0.05", amortization_years=20, maximum_ltv="0.65", minimum_dscr="1.25",
            payments_per_year=4, maturity_payments=8).items()})
        inputs = settings_for_acceptance()["rent_inputs"]
        inputs["bank_debt_yield"]["Base"].update(quote_document_id=parent["document_id"],quote_source_sha256=parent["source_sha256"])
        support = debt_tests.pdf_support(parent,inputs,"Base","D263-unreviewed",dict(C69="0.0501"))
        with patch.dict(transport.ALGORITHMS,{"plan_return_D107":"0"*64}):
            result = evaluate_trial("Base",dict(rows=[]),[],{},lambda *a,**k:self.fail("unreviewed algorithm reached a cash engine"),
                                    scenario_inputs=inputs,support=support,permanent=True,parent_bank=parent,exact=True)
        self.assertEqual(result["state"],"PENDING")
        self.assertIsNone(result["cash_per_usd_10"])
        self.assertIn("exact_cash_algorithm_revision_unconfirmed:plan_return_D107",result["blockers"])

    def test_v11_retains_bounded_pdf_case_size(self):
        # Use the supported technical profile explicitly, not an unregistered root.
        from miniuw_worksheet_v1 import WORKBOOK_TECHNICAL_ACCEPTANCE_SCHEMA
        case = dict(schema=WORKBOOK_TECHNICAL_ACCEPTANCE_SCHEMA,
                    rent_inputs=dict(sensitivities=dict(schema=EXACT_PERMANENT_SCHEMA)), padding="x"*55_000)
        self.assertEqual(read_case_source(encoded(case)), case)
        with self.assertRaises(ValueError):
            read_case_source(encoded(case | dict(padding="x"*100_000)))
        with self.assertRaises(ValueError):
            read_case_source(encoded(case | dict(schema="unsupported")))


class ExactCashIntegrationTests(TestCase):
    def check_cash(self, view, baseline):
        debt_tests.PermanentSensitivityIntegrationTests.check_loan_and_cash(self, view, baseline)
        descriptor = view["exact_cash_transport"]
        self.assertEqual(descriptor["profile"], transport.PROFILE)
        self.assertEqual(descriptor["max_integer_digits"], 1300)
        self.assertEqual(descriptor["rounding"], "none")
        self.assertFalse(descriptor["global_mutation"])
        self.assertEqual(len(descriptor["algorithms"]), len(transport.ALGORITHMS)+len(transport.DEPENDENCIES))

    def test_precision_case_full_cash_replay_and_legacy_compatibility(self):
        with TemporaryDirectory(prefix="miniuw-d263-") as temp:
            root = Path(temp)
            sources = source_files(root/"sources")
            registration = register(sources, "SYNTHETIC-D263-exact-cash")
            settings = settings_for_acceptance()
            assemble(settings,registration,sources,root/"origin")
            baseline = json.loads((root/"origin/results.json").read_bytes())
            inputs = settings["rent_inputs"]
            parents = {n:v["permanent_loan"]["bank_document_binding"]["quote"] for n,v in baseline["scenarios"].items()}
            inputs["sensitivities"] = debt_tests.request(parents,inputs)
            assemble(settings,registration,sources,root/"legacy-v10")
            legacy = json.loads((root/"legacy-v10/results.json").read_bytes())["sensitivity_evaluation"]
            inputs["sensitivities"] = request(parents,inputs)
            assemble(settings,registration,sources,root/"equivalent-v11")
            equivalent = json.loads((root/"equivalent-v11/results.json").read_bytes())["sensitivity_evaluation"]
            self.assertEqual(equivalent["state"], "computed_synthetic")
            for name,case in equivalent["scenarios"].items():
                for label,view in {**case["individual"],"combined":case["combined"]}.items():
                    self.check_cash(view,baseline["scenarios"][name])
                    old = legacy["scenarios"][name]["combined"] if label=="combined" else legacy["scenarios"][name]["individual"][label]
                    self.assertEqual(cash_values(view["cash_per_usd_10"]),cash_values(old["cash_per_usd_10"]))

            inputs["sensitivities"] = request(parents,inputs,precision=True)
            unchanged = deepcopy(settings)
            assemble(settings,registration,sources,root/"precision-v11")
            saved = read_package(root/"precision-v11")
            model = json.loads(saved["results.json"])
            self.assertEqual(settings,unchanged)
            self.assertEqual(model["scenarios"],baseline["scenarios"])
            self.assertEqual(model["decision"],"PENDING")
            self.assertFalse(model["deployment_enabled"])
            self.assertFalse(model["real_decisions_enabled"])
            result = model["sensitivity_evaluation"]
            self.assertEqual(result["state"],"computed_synthetic",{n:{c:v["blockers"] for c,v in s.get("individual",{}).items()} for n,s in result["scenarios"].items()})
            for name,case in result["scenarios"].items():
                for view in [*case["individual"].values(),case["combined"]]:
                    self.check_cash(view,baseline["scenarios"][name])
            principal = result["scenarios"]["Base"]["individual"]["C69"]["dated_debt_service"]["principal_due"]
            self.assertGreater(len(principal["numerator"]),256)
            self.assertEqual(verify_package(root/"precision-v11",current_revision_raw=saved[CURRENT_REVISION_FILE])["vigencia"],"VIGENTE")

            extended = deepcopy(settings)
            cases = extended["rent_inputs"]["sensitivities"]["scenarios"]
            cases["Base"]["changes"][1] = debt_tests.change("C70","30")
            cases["Base"]["permanent_support"]["individual"]["C70"] = debt_tests.pdf_support(parents["Base"],inputs,"Base","D263-30-years",dict(C70="30"))
            cases["Base"]["permanent_support"]["combined"] = debt_tests.pdf_support(parents["Base"],inputs,"Base","D263-30-combined",debt_tests.TARGETS["Base"]|dict(C69="0.0501",C70="30"))
            cases["Downside"]["changes"][0] = debt_tests.change("C69","0")
            cases["Downside"]["permanent_support"]["individual"]["C69"] = debt_tests.pdf_support(parents["Downside"],inputs,"Downside","D263-zero-rate",dict(C69="0"))
            cases["Downside"]["permanent_support"]["combined"] = debt_tests.pdf_support(parents["Downside"],inputs,"Downside","D263-zero-combined",debt_tests.TARGETS["Downside"]|dict(C69="0"))
            assemble(extended,registration,sources,root/"longer-and-zero")
            extra = json.loads((root/"longer-and-zero/results.json").read_bytes())["sensitivity_evaluation"]
            self.assertEqual(extra["state"],"computed_synthetic")
            for name,case in extra["scenarios"].items():
                self.check_cash(case["combined"],baseline["scenarios"][name])
            self.assertGreater(len(extra["scenarios"]["Base"]["combined"]["dated_debt_service"]["principal_due"]["denominator"]),500)
            self.assertEqual(amount(extra["scenarios"]["Downside"]["combined"]["dated_debt_service"]["interest_due"]),0)

            blocked = deepcopy(settings)
            cases = blocked["rent_inputs"]["sensitivities"]["scenarios"]
            for name,cell,value in (("Base","C72","5"),("Downside","C71","0.60")):
                i=list(debt_tests.PERMANENT_UNITS).index(cell)
                cases[name]["changes"][i] = debt_tests.change(cell,value)
                cases[name]["permanent_support"]["individual"][cell] = debt_tests.pdf_support(parents[name],inputs,name,"D263-over-"+cell,{cell:value})
                rate = "0.0501" if name=="Base" else "0.0651"
                cases[name]["permanent_support"]["combined"] = debt_tests.pdf_support(parents[name],inputs,name,"D263-over-combined",debt_tests.TARGETS[name]|dict(C69=rate)|{cell:value})
            assemble(blocked,registration,sources,root/"capacity-pending")
            limits = json.loads((root/"capacity-pending/results.json").read_bytes())["sensitivity_evaluation"]
            for name,cell in (("Base","C72"),("Downside","C71")):
                for view in (limits["scenarios"][name]["individual"][cell],limits["scenarios"][name]["combined"]):
                    self.assertIsNone(view["cash_per_usd_10"])
                    self.assertIn("selected_principal_exceeds_declared_bank_capacity",view["blockers"])

            missing = deepcopy(settings)
            cases = missing["rent_inputs"]["sensitivities"]["scenarios"]
            cases["Base"]["changes"][0]["value"] = None
            cases["Downside"]["permanent_support"]["individual"]["C69"]["source_ref"] = None
            cases["Downside"]["permanent_support"]["combined"]["source_ref"] = None
            assemble(missing,registration,sources,root/"missing-pending")
            rejected = json.loads((root/"missing-pending/results.json").read_bytes())["sensitivity_evaluation"]
            for case in rejected["scenarios"].values():
                self.assertIsNone(case["individual"]["C69"]["cash_per_usd_10"])
                self.assertIsNone(case["combined"]["cash_per_usd_10"])
                self.assertEqual(case["rank_by_signed_net_cash_delta"],[])
