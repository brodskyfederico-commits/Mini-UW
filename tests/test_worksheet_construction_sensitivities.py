"""Check C51-C53 individually and jointly against linked synthetic PDF quotes."""
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

import test_worksheet_budget_sensitivities as budget_tests
from test_worksheet_sensitivities import change as base_change
from check_worksheet_evidence_pdf_D156 import evidence_pdf
from check_worksheet_technical_acceptance_D200 import settings_for_acceptance, source_files
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, WORKBOOK_TECHNICAL_ACCEPTANCE_SCHEMA, encoded, read_case_source, read_package, verify_package
from worksheet_annual_coc import quantity as amount
from worksheet_construction_support_D257 import supported_quote
from worksheet_evidence_pdf_D156 import CONSTRUCTION_CONVENTIONS
from worksheet_intake_D198 import assemble, register
from worksheet_sensitivities_D253 import CONSTRUCTION_SCHEMA, bind_change, evaluate_scenario


UNITS = dict(C51="fraction", C52="annual_nominal_fraction", C53="fraction_of_commitment")
TARGETS = {"Base": dict(C51="0.65", C52="0.09", C53="0"), "Downside": dict(C51="0.40", C52="0.11", C53="0.02")}


def change(cell, operation, unit, value):
    return base_change(cell, operation, unit, value) | dict(source_ref=f"SYNTHETIC-D257-explicit-{cell}")


def literal(value):
    number = amount(value)
    return format(Decimal(number.numerator)/Decimal(number.denominator), "f")


def pdf_support(parent, name, label, edits, *, extra=None, omit=None, page_name=None):
    values = deepcopy(parent["document"])
    for cell, field in dict(C51="ltc", C52="annual_interest", C53="origination_fee_fraction").items():
        if cell in edits:
            values[field] = rational(Fraction(edits[cell]))
    values.update(extra or {})
    revision = f"SYNTHETIC-D257-{name}-{label}"
    lines = [f"SYNTHETIC MINI-UW CONSTRUCTION TERMS {(page_name or name).upper()}",
             f"Document ID | SYNTHETIC-D257-{name}-{label}-CONSTRUCTION", f"Revision | {revision}",
             "Case ID | SYNTHETIC-D140-rental-return"]
    units = dict(C51=("ltc", "fraction"), C52=("annual_interest", "annual_nominal_fraction"),
                 C53=("origination_fee_fraction", "fraction_of_commitment"),
                 **{"Maximum commitment": ("maximum_commitment", "USD"),
                    "Requested invoice share": ("requested_invoice_fraction", "fraction"),
                    "Available per draw": ("available_per_draw_checkpoint", "USD")})
    lines += [f"{key} | {unit} | {literal(values[field])}" for key, (field, unit) in units.items() if key != omit]
    lines += [f"Maturity date | {values['maturity_date']}", *(f"{key} | {value}" for key, value in CONSTRUCTION_CONVENTIONS.items())]
    raw = evidence_pdf(dict(terms=lines), order=("terms",))
    writer = PdfWriter()
    writer.add_page(PdfReader(BytesIO(raw), strict=True).pages[0])
    writer.pages[0].compress_content_streams()
    stream = BytesIO()
    writer.write(stream)
    raw = stream.getvalue()
    return dict(source_ref=revision+"-support", revision=revision, parent_document_id=parent["document_id"],
                parent_sha256=parent["source_sha256"], pdf_sha256=sha(raw), pdf_base64=base64.b64encode(raw).decode())


def request(parents):
    cases = {}
    for name in ("Base", "Downside"):
        changes = [change("C51", "percentage_point_change", "percentage_points", 5 if name == "Base" else -10),
                   change("C52", "basis_point_change", "bps", 100),
                   change("C53", "replace_absolute", UNITS["C53"], 0) if name == "Base"
                   else change("C53", "basis_point_change", "bps", 50)]
        cases[name] = dict(changes=changes, construction_support=dict(
            individual={cell: pdf_support(parents[name], name, cell, {cell: value}) for cell, value in TARGETS[name].items()},
            combined=pdf_support(parents[name], name, "combined", TARGETS[name])))
    return dict(schema=CONSTRUCTION_SCHEMA, scenarios=cases)


class ConstructionSensitivityBindingTests(TestCase):
    def test_larger_case_limit_is_scoped_to_synthetic_construction_support(self):
        case = dict(schema=WORKBOOK_TECHNICAL_ACCEPTANCE_SCHEMA, rent_inputs=dict(sensitivities=dict(schema=CONSTRUCTION_SCHEMA)), padding="x"*55_000)
        self.assertEqual(read_case_source(encoded(case)), case)
        with self.assertRaises(ValueError):
            read_case_source(encoded(case | dict(schema="unsupported")))
        with self.assertRaises(ValueError):
            read_case_source(encoded(case | dict(rent_inputs=dict(sensitivities=dict(schema="miniuw.synthetic-worksheet-sensitivities.v4")))))
        with self.assertRaises(ValueError):
            read_case_source(encoded(case | dict(padding="x"*100_000)))

    def test_blanks_missing_sources_and_units_block_but_numeric_zero_is_preserved(self):
        for cell, unit in UNITS.items():
            row = dict(field_id=f"INPUT_{cell}", value_cell=f"Inputs!{cell}", state="CONFIRMED_SYNTHETIC", value=rational(Fraction(1, 2)))
            request = change(cell, "replace_absolute", unit, 0)
            review = dict(workbook_sha256="book", rows=[dict(field_id="INPUT_C7", value="PER UNIT"), row])
            self.assertEqual(amount(bind_change(request, {row["field_id"]: row}, "book", "case", units=UNITS)["resulting_value"]), 0)
            invalid = [request | dict(value=value) for value in (None, "", " ")]
            invalid += [{key: value for key, value in request.items() if key != missing} for missing in ("value", "source_ref")]
            invalid += [request | dict(unit="monthly_fraction")]
            for entry in invalid:
                record = dict(changes=[entry], construction_support=dict(individual={cell: {}}, combined={}))
                result = evaluate_scenario(record, "Base", review, dict(cash_per_usd_10={}),
                    lambda *args, **kw: self.fail("invalid financial input reached the engine"), [], "case", extended=True,
                    budget=True, construction=True, scenario_inputs={})
                self.assertEqual(result["state"], "PENDING")
                self.assertIsNone(result["combined"]["cash_per_usd_10"])
                self.assertEqual(result["rank_by_signed_net_cash_delta"], [])
            for blank in (None, "", " "):
                with self.assertRaises((ValueError, TypeError)):
                    bind_change(request, {row["field_id"]: row | dict(value=blank)}, "book", "case", units=UNITS)

    def test_quote_hash_scope_rows_and_unchanged_bank_limits_are_required(self):
        parent = dict(document_id="SYNTHETIC-D257-parent", revision="SYNTHETIC-D257-prior", source_sha256="a"*64,
                      blockers=[], state="checked_synthetic", document=dict(
                          ltc=rational(Fraction(3, 5)), annual_interest=rational(Fraction(2, 25)), origination_fee_fraction=rational(Fraction(1, 100)),
                          maximum_commitment=rational(1_600_000), requested_invoice_fraction=rational(Fraction(1, 4)),
                          available_per_draw_checkpoint=rational(350_000), maturity_date="2028-12-30"))
        before = deepcopy(parent)
        valid = pdf_support(parent, "Base", "zero-rate", dict(C52="0"))
        quote, proof = supported_quote(valid, "Base", "SYNTHETIC-D140-rental-return", parent)
        self.assertEqual(amount(quote["document"]["annual_interest"]), 0)
        self.assertEqual(proof["observed_pdf_sha256"], valid["pdf_sha256"])
        self.assertEqual(quote["extraction_method"], "pdf_text")
        self.assertEqual(parent, before)
        bad = [valid | dict(pdf_sha256="0"*64), valid | dict(parent_sha256="0"*64), valid | dict(pdf_base64="!"),
               pdf_support(parent, "Base", "missing", {}, omit="C52"),
               pdf_support(parent, "Base", "other-scenario", {}, page_name="Downside"),
               pdf_support(parent, "Base", "other-limit", {}, extra=dict(maximum_commitment=rational(2_000_000)))]
        for record in bad:
            with self.assertRaises((ValueError, TypeError)):
                supported_quote(record, "Base", "SYNTHETIC-D140-rental-return", parent)


class ConstructionSensitivityIntegrationTests(TestCase):
    def test_three_rates_replay_draws_interest_fees_and_joint_cash_with_pending_controls(self):
        with TemporaryDirectory(prefix="miniuw-d257-") as temp:
            root = Path(temp)
            sources = source_files(root / "sources")
            registration = register(sources, "SYNTHETIC-D257-construction")
            settings = settings_for_acceptance()
            assemble(settings, registration, sources, root / "origin")
            original = json.loads((root / "origin/results.json").read_bytes())
            parents = {name: original["scenarios"][name]["construction_financing"]["bank_document_binding"]["quote"]
                       for name in ("Base", "Downside")}
            settings["rent_inputs"]["sensitivities"] = request(parents)
            unchanged = deepcopy(settings)
            assemble(settings, registration, sources, root / "variants")
            saved = read_package(root / "variants")
            model = json.loads(saved["results.json"])
            self.assertEqual(settings, unchanged)
            self.assertEqual(model["scenarios"], original["scenarios"])
            self.assertEqual(model["decision"], "PENDING")
            sensitivity = model["sensitivity_evaluation"]
            self.assertEqual(sensitivity["state"], "computed_synthetic", {
                name: {cell: row["blockers"] for cell, row in case.get("individual", {}).items()}
                for name, case in sensitivity["scenarios"].items()})
            for name in ("Base", "Downside"):
                baseline = original["scenarios"][name]
                case = sensitivity["scenarios"][name]
                for label, variant in (case["individual"] | dict(combined=case["combined"])).items():
                    budget_tests.BudgetSensitivityIntegrationTests.check_finance(self, variant)
                    funding = variant["construction_financing"]
                    self.assertEqual(variant["project_calendar"], baseline["project_calendar"])
                    self.assertEqual(variant["cash_per_usd_10"]["total_distributions"], baseline["cash_per_usd_10"]["total_distributions"])
                    self.assertEqual(funding["construction_principal_payoff"], baseline["construction_financing"]["construction_principal_payoff"])
                    self.assertEqual([row["draw_at_start"] for row in funding["debt_run"]["periods"]],
                                     [row["draw_at_start"] for row in baseline["construction_financing"]["debt_run"]["periods"]])
                    self.assertEqual(amount(funding["origination_fee"]), amount(funding["commitment"])*amount(funding["origination_fee_fraction"]))
                    self.assertEqual(amount(funding["debt_run"]["totals"]["interest_due"])*amount(baseline["construction_financing"]["annual_interest"]),
                                     amount(baseline["construction_financing"]["debt_run"]["totals"]["interest_due"])*amount(funding["annual_interest"]))
                    bank = funding["bank_document_binding"]["quote"]
                    self.assertEqual(bank["parent_source_sha256"], parents[name]["source_sha256"])
                    self.assertEqual(bank["source_sha256"], variant["construction_support"]["observed_pdf_sha256"])
                    for binding in variant["bindings"]:
                        cell = binding["change"]["target_cell"]
                        self.assertEqual(funding["cell_sources"][cell], f"sha256:{sha(encoded(binding))}#/resulting_value")
                self.assertEqual(amount(case["individual"]["C51"]["construction_financing"]["commitment"]),
                                 1_600_000 if name == "Base" else 1_097_600)
                self.assertNotEqual(amount(case["combined"]["delta_net_cash_per_usd_10"]),
                                    sum(amount(row["delta_net_cash_per_usd_10"]) for row in case["individual"].values()))
            self.assertEqual(amount(sensitivity["scenarios"]["Base"]["combined"]["construction_financing"]["origination_fee"]), 0)
            self.assertEqual(verify_package(root / "variants", current_revision_raw=saved[CURRENT_REVISION_FILE])["vigencia"], "VIGENTE")

            missing = deepcopy(settings)
            records = missing["rent_inputs"]["sensitivities"]["scenarios"]
            records["Base"]["construction_support"]["individual"]["C52"] = {}
            records["Downside"]["construction_support"]["individual"]["C53"] = pdf_support(parents["Downside"], "Downside", "contradiction", {})
            assemble(missing, registration, sources, root / "missing-support")
            rejected = json.loads((root / "missing-support/results.json").read_bytes())["sensitivity_evaluation"]
            for name, cell, reason in (("Base", "C52", "construction_support_parent_or_revision_unconfirmed"),
                                      ("Downside", "C53", "B08:construction_pdf_and_worksheet_terms_disagree")):
                row = rejected["scenarios"][name]["individual"][cell]
                self.assertEqual(row["state"], "PENDING")
                self.assertIsNone(row["cash_per_usd_10"])
                self.assertIn(reason, row["blockers"])
                self.assertEqual(rejected["scenarios"][name]["rank_by_signed_net_cash_delta"], [])

            zero = deepcopy(settings)
            cases = zero["rent_inputs"]["sensitivities"]["scenarios"]
            for name, cell in (("Base", "C52"), ("Downside", "C51")):
                index = list(UNITS).index(cell)
                cases[name]["changes"][index] = change(cell, "replace_absolute", UNITS[cell], 0)
                cases[name]["construction_support"]["individual"][cell] = pdf_support(parents[name], name, "explicit-zero", {cell: "0"})
                cases[name]["construction_support"]["combined"] = pdf_support(parents[name], name, "joint-zero", TARGETS[name] | {cell: "0"})
            assemble(zero, registration, sources, root / "zero-controls")
            zero_result = json.loads((root / "zero-controls/results.json").read_bytes())["sensitivity_evaluation"]
            base = zero_result["scenarios"]["Base"]["individual"]["C52"]
            self.assertEqual(base["state"], "computed_synthetic")
            self.assertEqual(amount(base["construction_financing"]["debt_run"]["totals"]["interest_due"]), 0)
            for label, row in (("single", zero_result["scenarios"]["Downside"]["individual"]["C51"]),
                               ("joint", zero_result["scenarios"]["Downside"]["combined"])):
                self.assertEqual(row["state"], "PENDING", label)
                self.assertIsNone(row["cash_per_usd_10"])
                self.assertEqual(amount(row["construction_financing"]["commitment"]), 0)
                self.assertTrue(any("cumulative_gross_draws_exceed_nonrevolving_commitment" in reason for reason in row["blockers"]))
