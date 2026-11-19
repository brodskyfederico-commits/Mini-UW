"""Replay C69-C72 against revised bank PDFs, exact debt schedules and gross cash."""
import base64
from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from pypdf import PdfReader, PdfWriter

from check_worksheet_evidence_pdf_D156 import evidence_pdf
from check_worksheet_technical_acceptance_D200 import settings_for_acceptance, source_files, verify_periods
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, MAX_CONSTRUCTION_PILOT_BYTES, WORKBOOK_TECHNICAL_ACCEPTANCE_SCHEMA, encoded, read_case_source, read_package, verify_package
from test_worksheet_sensitivities import change as base_change
from worksheet_annual_coc import quantity as amount
from worksheet_evidence_pdf_D156 import BANK_CONVENTIONS, BANK_ROWS
from worksheet_intake_D198 import assemble, register
from worksheet_permanent_support_D262 import supported_terms
from worksheet_sensitivities_D253 import PERMANENT_SCHEMA, PERMANENT_UNITS, bind_change, evaluate_scenario


TARGETS = {"Base": dict(C69="0.06", C70="21", C71="0.6499", C72="1.251"),
           "Downside": dict(C69="0.064", C70="12", C71="0.6499", C72="1.301")}


def change(cell, value):
    return base_change(cell, "replace_absolute", PERMANENT_UNITS[cell], Fraction(value)) | dict(source_ref=f"SYNTHETIC-D262-explicit-{cell}")


def literal(value):
    f = amount(value)
    return format(Decimal(f.numerator)/Decimal(f.denominator), "f")


def pdf_support(parent, inputs, name, label, edits, *, extra=None, omit=None, page_name=None):
    values = deepcopy(parent["document"])
    for cell, field in dict(C69="annual_nominal_rate", C70="amortization_years", C71="maximum_ltv", C72="minimum_dscr").items():
        if cell in edits:
            values[field] = rational(Fraction(edits[cell]))
    values.update(extra or {})
    revision = f"SYNTHETIC-D262-{name}-{label}"
    document_id = revision+"-BANK"
    lines = [f"SYNTHETIC MINI-UW BANK TERMS {(page_name or name).upper()}", f"Document ID | {document_id}",
             f"Revision | {revision}", "Case ID | SYNTHETIC-D140-rental-return"]
    lines += [f"{key} | {unit} | {literal(values[field])}" for key, (field, unit) in BANK_ROWS.items() if key != omit]
    lines += [f"{key} | {value}" for key, value in BANK_CONVENTIONS.items()]
    raw = evidence_pdf(dict(bank=lines), order=("bank",))
    writer = PdfWriter()
    writer.add_page(PdfReader(BytesIO(raw), strict=True).pages[0])
    writer.pages[0].compress_content_streams()
    stream = BytesIO()
    writer.write(stream)
    raw = stream.getvalue()
    old = inputs["bank_debt_yield"][name]
    return dict(source_ref=revision+"-support", revision=revision, parent_document_id=parent["document_id"],
                parent_sha256=parent["source_sha256"], pdf_sha256=sha(raw), pdf_base64=base64.b64encode(raw).decode(),
                parent_addendum_sha256=sha(encoded(old)), debt_yield_addendum=old | dict(
                    source_ref=revision+"-debt-yield", quote_document_id=document_id, quote_source_sha256=sha(raw)))


def request(parents, inputs):
    return dict(schema=PERMANENT_SCHEMA, scenarios={name: dict(
        changes=[change(c, v) for c, v in TARGETS[name].items()], permanent_support=dict(
            individual={c: pdf_support(parents[name], inputs, name, c, {c: v}) for c, v in TARGETS[name].items()},
            combined=pdf_support(parents[name], inputs, name, "combined", TARGETS[name]))) for name in TARGETS})


def event(cash, key):
    row, = [e for e in cash["events"] if e["event_id"] == key]
    return amount(row["amount"])


class PermanentSensitivityBindingTests(TestCase):
    def test_blanks_units_whole_years_and_multiple_operations(self):
        for cell, unit in PERMANENT_UNITS.items():
            row = dict(field_id=f"INPUT_{cell}", value_cell=f"Inputs!{cell}", state="CONFIRMED_SYNTHETIC", value=rational(1))
            zero = change(cell, 0)
            self.assertEqual(amount(bind_change(zero, {row["field_id"]: row}, "book", "case", units=PERMANENT_UNITS)["resulting_value"]), 0)
            review = dict(workbook_sha256="book", rows=[dict(field_id="INPUT_C7", value="PER UNIT"), row])
            for blank in (None, "", " "):
                with self.assertRaises((ValueError, TypeError)):
                    bind_change(zero, {row["field_id"]: row | dict(value=blank)}, "book", "case", units=PERMANENT_UNITS)
                spec = dict(changes=[zero | dict(value=blank)], permanent_support=dict(individual={cell: {}}, combined={}))
                outcome = evaluate_scenario(spec, "Base", review, dict(cash_per_usd_10={}),
                    lambda *a, **k: self.fail("blank reached engine"), [], "case", extended=True, permanent=True)
                self.assertEqual(outcome["state"], "PENDING")
                self.assertIsNone(outcome["combined"]["cash_per_usd_10"])
            for invalid in (zero | dict(unit="undeclared_unit"), zero | dict(source_ref=None)):
                with self.assertRaises(ValueError):
                    bind_change(invalid, {row["field_id"]: row}, "book", "case", units=PERMANENT_UNITS)
        for cell, edit in (("C70", dict(value=rational(Fraction(1, 2)))), ("C70", dict(operation="basis_point_change", unit="bps")),
                           ("C72", dict(operation="percentage_point_change", unit="percentage_points"))):
            row = dict(field_id=f"INPUT_{cell}", value_cell=f"Inputs!{cell}", state="CONFIRMED_SYNTHETIC", value=rational(1))
            with self.assertRaises(ValueError):
                bind_change(change(cell, 1) | edit, {row["field_id"]: row}, "book", "case", units=PERMANENT_UNITS)

    def test_larger_json_limit_only_for_supported_pdf_profiles(self):
        case = dict(schema=WORKBOOK_TECHNICAL_ACCEPTANCE_SCHEMA, rent_inputs=dict(sensitivities=dict(schema=PERMANENT_SCHEMA)), padding="x"*55_000)
        self.assertEqual(read_case_source(encoded(case)), case)
        invalid_cases = [case | dict(schema="unsupported"),
                         case | dict(rent_inputs=dict(sensitivities=dict(schema="miniuw.synthetic-worksheet-sensitivities.v9")))]
        for invalid in invalid_cases:
            with self.assertRaises(ValueError):
                read_case_source(encoded(invalid))
        with self.assertRaises(ValueError):
            read_case_source(encoded(case | dict(padding="x"*100_000)))

    def test_pdf_parent_scope_unchanged_contract_and_debt_yield_must_match(self):
        parent = dict(document_id="SYNTHETIC-D262-parent", revision="SYNTHETIC-D262-prior", source_sha256="a"*64,
            blockers=[], document={k:rational(Fraction(v)) for k,v in dict(requested_principal=1_400_000,
            annual_nominal_rate="0.05", amortization_years=20, maximum_ltv="0.65", minimum_dscr="1.25", payments_per_year=4, maturity_payments=8).items()})
        inputs = settings_for_acceptance()["rent_inputs"]
        inputs["bank_debt_yield"]["Base"].update(quote_document_id=parent["document_id"], quote_source_sha256=parent["source_sha256"])
        original = deepcopy(inputs)
        valid = pdf_support(parent, inputs, "Base", "zero-rate", dict(C69="0"))
        quote, updated, proof = supported_terms(valid, "Base", inputs, parent)
        self.assertEqual(inputs, original)
        self.assertEqual(amount(quote["document"]["annual_nominal_rate"]), 0)
        self.assertEqual(updated["bank_debt_yield"]["Base"]["quote_source_sha256"], valid["pdf_sha256"])
        self.assertEqual(proof["observed_pdf_sha256"], valid["pdf_sha256"])
        self.assertEqual(updated["bank_debt_yield"]["Base"]["minimum"], original["bank_debt_yield"]["Base"]["minimum"])
        invalid = [valid | dict(pdf_sha256="0"*64), valid | dict(parent_sha256="0"*64), valid | dict(parent_addendum_sha256="0"*64),
            valid | dict(pdf_base64="!"), pdf_support(parent, inputs, "Base", "missing", {}, omit="C72"),
            pdf_support(parent, inputs, "Base", "other-scenario", {}, page_name="Downside"),
            pdf_support(parent, inputs, "Base", "other-principal", {}, extra=dict(requested_principal=rational(1_500_000))),
            pdf_support(parent, inputs, "Base", "other-maturity", {}, extra=dict(maturity_payments=rational(12))),
            valid | dict(debt_yield_addendum=valid["debt_yield_addendum"] | dict(minimum=rational(Fraction(1, 2)))),
            valid | dict(debt_yield_addendum=valid["debt_yield_addendum"] | dict(quote_source_sha256=parent["source_sha256"]))]
        for record in invalid:
            with self.assertRaises((ValueError, TypeError)):
                supported_terms(record, "Base", inputs, parent)


class PermanentSensitivityIntegrationTests(TestCase):
    def check_loan_and_cash(self, view, baseline):
        verify_periods(view)
        loan, old = view["permanent_loan"], baseline["permanent_loan"]
        cash, old_cash = view["cash_per_usd_10"], baseline["cash_per_usd_10"]
        p = amount(loan["requested_principal"])
        r = amount(loan["annual_nominal_rate"])/4
        n = loan["amortization_years"]*4
        unit = Fraction(1, n) if r == 0 else r/(1-(1+r)**(-n))
        payment, interest = p*unit, p*r
        payoff = p-(payment-interest)
        self.assertEqual(loan["amortization_payments"], n)
        self.assertEqual(amount(loan["regular_payment_due"]), payment)
        self.assertEqual(amount(loan["annual_sizing_service"]), 4*payment)
        self.assertEqual(loan["maturity_payments"], old["maturity_payments"])
        self.assertEqual(loan["maturity_date"], old["maturity_date"])
        self.assertEqual(loan["payment_dates"], old["payment_dates"])
        balance = p
        for row in loan["projected_schedule"]:
            self.assertEqual(amount(row["opening_balance"]), balance)
            self.assertEqual(amount(row["interest_due"]), balance*r)
            self.assertEqual(amount(row["principal_due"]), payment-balance*r)
            balance -= payment-balance*r
            self.assertEqual(amount(row["closing_balance"]), balance)
        self.assertEqual(amount(view["debt_principal_paid_at_sale"]), payoff)
        self.assertEqual(amount(view["dated_debt_service"]["scheduled_service_due"]), payment)
        cap = view["capacity"]
        ltv = amount(view["valuation_and_sale"]["refinance_value"])*amount(loan["maximum_ltv"])
        dscr = amount(cap["bank_noi"])/(amount(loan["minimum_dscr"])*4*unit)
        self.assertEqual(amount(cap["capacity_limits"]["LTV"]), ltv)
        self.assertEqual(amount(cap["capacity_limits"]["DSCR"]), dscr)
        self.assertEqual(cap["capacity_limits"]["DEBT_YIELD"], baseline["capacity"]["capacity_limits"]["DEBT_YIELD"])
        limits = {k:amount(v) for k,v in cap["capacity_limits"].items()}
        self.assertEqual(amount(cap["maximum_principal_capacity"]), min(limits.values()))
        self.assertEqual(set(cap["binding_limit_ids"]), {k for k,v in limits.items() if v == min(limits.values())})
        self.assertEqual(cap["selected_principal"], baseline["capacity"]["selected_principal"])
        self.assertEqual(view["noi_by_period"], baseline["noi_by_period"])
        self.assertEqual(view["gross_sale"], baseline["gross_sale"])
        self.assertEqual(view["construction_financing"], baseline["construction_financing"])
        self.assertEqual(cash["scale_factor"], old_cash["scale_factor"])
        self.assertEqual(event(cash, "initial"), 10)
        self.assertEqual(cash["total_contributions"], old_cash["total_contributions"])
        self.assertEqual(event(cash, "refinance"), event(old_cash, "refinance"))
        scale = amount(cash["scale_factor"])
        self.assertEqual(event(cash, "operating")-event(old_cash, "operating"),
                         (amount(baseline["dated_debt_service"]["scheduled_service_due"])-payment)*scale)
        self.assertEqual(event(cash, "sale")-event(old_cash, "sale"), (amount(baseline["debt_principal_paid_at_sale"])-payoff)*scale)
        self.assertEqual(amount(cash["total_distributions"])-amount(old_cash["total_distributions"]),
                         -p*(r-amount(old["periodic_rate"]))*scale)
        self.assertEqual(amount(cash["unrecovered_after_sale"]), max(0, amount(cash["total_contributions"])-amount(cash["total_distributions"])))
        for kind,total in (("contribution","total_contributions"),("distribution","total_distributions")):
            self.assertEqual(sum(amount(e["amount"]) for e in cash["events"] if e["kind"]==kind), amount(cash[total]))
        quote = loan["bank_document_binding"]["quote"]
        self.assertEqual(loan["bank_document_binding"]["blockers"], [])
        self.assertEqual(cap["debt_yield"]["quote_document_id"], quote["document_id"])
        self.assertEqual(cap["debt_yield"]["quote_source_sha256"], quote["source_sha256"])
        self.assertEqual(cap["debt_yield"]["minimum"], baseline["capacity"]["debt_yield"]["minimum"])
        for b in view["bindings"]:
            self.assertEqual(loan["cell_sources"][b["change"]["target_cell"]], f"sha256:{sha(encoded(b))}#/resulting_value")

    def test_individual_joint_bank_binding_capacity_missing_and_zero(self):
        with TemporaryDirectory(prefix="miniuw-d262-") as temp:
            root = Path(temp)
            sources = source_files(root/"sources")
            registration = register(sources, "SYNTHETIC-D262-permanent")
            settings = settings_for_acceptance()
            assemble(settings, registration, sources, root/"origin")
            original = json.loads((root/"origin/results.json").read_bytes())
            inputs = settings["rent_inputs"]
            parents = {name:v["permanent_loan"]["bank_document_binding"]["quote"] for name,v in original["scenarios"].items()}
            inputs["sensitivities"] = request(parents, inputs)
            unchanged = deepcopy(settings)
            assemble(settings, registration, sources, root/"variants")
            saved = read_package(root/"variants")
            self.assertLessEqual(len(saved["case.json"]), MAX_CONSTRUCTION_PILOT_BYTES)
            self.assertEqual(settings, unchanged)
            model = json.loads(saved["results.json"])
            self.assertEqual(model["scenarios"], original["scenarios"])
            self.assertEqual(model["decision"], "PENDING")
            self.assertFalse(model["deployment_enabled"])
            result = model["sensitivity_evaluation"]
            self.assertEqual(result["state"], "computed_synthetic", {name:{c:v["blockers"] for c,v in s.get("individual",{}).items()} for name,s in result["scenarios"].items()})
            for name,case in result["scenarios"].items():
                for view in [*case["individual"].values(),case["combined"]]:
                    self.check_loan_and_cash(view, original["scenarios"][name])
                for cell in ("C70", "C71", "C72"):
                    self.assertEqual(case["individual"][cell]["cash_per_usd_10"]["total_distributions"], original["scenarios"][name]["cash_per_usd_10"]["total_distributions"])
            self.assertEqual(verify_package(root/"variants", current_revision_raw=saved[CURRENT_REVISION_FILE])["vigencia"], "VIGENTE")

            missing = deepcopy(settings)
            cases = missing["rent_inputs"]["sensitivities"]["scenarios"]
            cases["Base"]["permanent_support"]["individual"]["C69"]["source_ref"] = None
            cases["Base"]["permanent_support"]["combined"]["source_ref"] = None
            cases["Downside"]["changes"][1]["value"] = None
            assemble(missing, registration, sources, root/"missing-support")
            rejected = json.loads((root/"missing-support/results.json").read_bytes())["sensitivity_evaluation"]
            for name,cell in (("Base","C69"),("Downside","C70")):
                case = rejected["scenarios"][name]
                self.assertIsNone(case["individual"][cell]["cash_per_usd_10"])
                self.assertIsNone(case["combined"]["cash_per_usd_10"])
                self.assertEqual(case["rank_by_signed_net_cash_delta"], [])

            conflict = deepcopy(settings)
            cases = conflict["rent_inputs"]["sensitivities"]["scenarios"]
            cases["Base"]["permanent_support"]["individual"]["C69"] = pdf_support(parents["Base"], inputs, "Base", "conflict", dict(C69="0.07"))
            cases["Downside"]["permanent_support"]["individual"]["C69"]["debt_yield_addendum"]["minimum"] = rational(Fraction(1,2))
            assemble(conflict, registration, sources, root/"document-conflicts")
            conflicted = json.loads((root/"document-conflicts/results.json").read_bytes())["sensitivity_evaluation"]
            for name,reason in (("Base","B08:bank_pdf_and_worksheet_terms_disagree"),("Downside","permanent_support_changes_debt_yield_terms")):
                case = conflicted["scenarios"][name]
                self.assertIn(reason,case["individual"]["C69"]["blockers"])
                self.assertIsNone(case["individual"]["C69"]["cash_per_usd_10"])
                self.assertEqual(case["rank_by_signed_net_cash_delta"], [])

            controls = deepcopy(settings)
            cases = controls["rent_inputs"]["sensitivities"]["scenarios"]
            for name,cell,value in (("Base","C72","5"),("Downside","C71","0.60")):
                i=list(PERMANENT_UNITS).index(cell)
                cases[name]["changes"][i] = change(cell,value)
                cases[name]["permanent_support"]["individual"][cell] = pdf_support(parents[name],inputs,name,"over-"+cell,{cell:value})
                cases[name]["permanent_support"]["combined"] = pdf_support(parents[name],inputs,name,"over-combined",TARGETS[name]|{cell:value})
            assemble(controls, registration, sources, root/"capacity-blocks")
            blocked = json.loads((root/"capacity-blocks/results.json").read_bytes())["sensitivity_evaluation"]
            for name,cell,limit in (("Base","C72","DSCR"),("Downside","C71","LTV")):
                case=blocked["scenarios"][name]
                for trial in (case["individual"][cell],case["combined"]):
                    self.assertIn("selected_principal_exceeds_declared_bank_capacity",trial["blockers"])
                    self.assertIsNone(trial["cash_per_usd_10"])
                    self.assertIsNone(trial["construction_refinance"]["net_equity_distribution"])
                    self.assertEqual(trial["capacity"]["binding_limit_ids"],[limit])
                    self.assertLess(amount(trial["capacity"]["maximum_principal_capacity"]),amount(trial["capacity"]["selected_principal"]))

            zeros=deepcopy(settings)
            cases=zeros["rent_inputs"]["sensitivities"]["scenarios"]
            for name,edits in (("Base",dict(C69="0",C71="0")),("Downside",dict(C69="0",C70="0",C72="0"))):
                for cell,value in edits.items():
                    i=list(PERMANENT_UNITS).index(cell)
                    cases[name]["changes"][i]=change(cell,value)
                    cases[name]["permanent_support"]["individual"][cell]=pdf_support(parents[name],inputs,name,"zero-"+cell,{cell:value})
                cases[name]["permanent_support"]["combined"]=pdf_support(parents[name],inputs,name,"zero-combined",TARGETS[name]|edits)
            assemble(zeros,registration,sources,root/"zero-controls")
            zero=json.loads((root/"zero-controls/results.json").read_bytes())["sensitivity_evaluation"]
            for name in TARGETS:
                trial=zero["scenarios"][name]["individual"]["C69"]
                self.check_loan_and_cash(trial,original["scenarios"][name])
                self.assertEqual(amount(trial["dated_debt_service"]["interest_due"]),0)
                self.assertIsNone(zero["scenarios"][name]["combined"]["cash_per_usd_10"])
            for name,cell in (("Base","C71"),("Downside","C70"),("Downside","C72")):
                self.assertIsNone(zero["scenarios"][name]["individual"][cell]["cash_per_usd_10"])

            precision=deepcopy(settings)
            case=precision["rent_inputs"]["sensitivities"]["scenarios"]["Base"]
            case["changes"][0]=change("C69","0.0501")
            case["permanent_support"]["individual"]["C69"]=pdf_support(parents["Base"],inputs,"Base","precision-C69",dict(C69="0.0501"))
            case["permanent_support"]["combined"]=pdf_support(parents["Base"],inputs,"Base","precision-combined",TARGETS["Base"]|dict(C69="0.0501"))
            assemble(precision,registration,sources,root/"precision-pending")
            bounded=json.loads((root/"precision-pending/results.json").read_bytes())["sensitivity_evaluation"]
            base=bounded["scenarios"]["Base"]
            for trial in (base["individual"]["C69"],base["combined"]):
                self.assertIn("permanent_exact_cash_transport_precision_unsupported",trial["blockers"])
                self.assertIsNone(trial["cash_per_usd_10"])
                self.assertFalse(trial["technical_limit"]["rounding_applied"])
            self.assertEqual(base["rank_by_signed_net_cash_delta"],[])
            self.assertEqual(bounded["scenarios"]["Downside"]["state"],"computed_synthetic")
