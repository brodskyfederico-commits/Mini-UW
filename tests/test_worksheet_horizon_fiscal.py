"""Dated M2 cash, complete fiscal evidence and current one-page delivery."""
from copy import deepcopy
from fractions import Fraction as Q
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))

from audit_worksheet_critical_evidence_D219 import audit
from check_worksheet_holding_horizon_D266 import sources_for
from check_worksheet_horizon_fiscal_D267 import settings,source_cells,independent_taxes,independently_verify,value
from miniuw_foundation.debt_service import rational
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE,WORKBOOK_FLORIDA_TAX_SCHEMA,encoded,read_package,verify_package,deliver_package
from plan_return_D107 import FORWARD_PERIOD
from test_worksheet_exact_cash import cash_values
import worksheet_horizon_fiscal_D267 as fiscal
from worksheet_intake_D198 import assemble,register


class FiscalHorizonContractTests(TestCase):
    @classmethod
    def setUpClass(cls):
        temp=TemporaryDirectory(prefix="miniuw-d267-contract-");cls.addClassCleanup(temp.cleanup)
        cls.spec=settings();cls.sources=sources_for(cls.spec,Path(temp.name)/"sources")

    def calendar(self,name):
        inputs=self.spec["rent_inputs"];_,cell=source_cells(self.sources,name)
        review=dict(workbook_sha256="a"*64,rows=[dict(value_cell="Inputs!"+key,state="CONFIRMED_SYNTHETIC",value=rational(cell(key)))
            for key in ("C46","C47")])
        return fiscal.horizon_calendar(inputs["project_calendar"],name,review,inputs["development"]["scenarios"][name]["purchase_date"],
            inputs["supplemental_scope"][name]["sale_date"],inputs["holding_horizon"])

    def test_dated_tax_matches_independent_rolls_and_handles_january_without_buyer_window(self):
        inputs=self.spec["rent_inputs"]
        for name in ("Base","Downside"):
            taxes,first,cash=fiscal.fiscal_cash(inputs["florida_property_tax"],inputs["holding_tax_cash"],name,self.calendar(name))
            self.assertEqual(taxes,independent_taxes(self.spec,self.sources,name))
            self.assertEqual(first,taxes["SYNTHETIC-D107-operating-year"])
            self.assertEqual(value(cash["preopening_tax_total"]),Q("16631.25") if name=="Base" else Q("36131.25"))
            self.assertEqual(sum(value(q["total"]) for q in cash["quarterly_taxes"]),value(cash["operating_tax_total"]))
        base=deepcopy(inputs["florida_property_tax"]);base["scenarios"]["Base"]["rolls"]["buyer"]={}
        taxes,_,_=fiscal.fiscal_cash(base,inputs["holding_tax_cash"],"Base",self.calendar("Base"))
        self.assertEqual({r["owner"] for r in taxes[FORWARD_PERIOD]["rolls"]},{"seller"})
        down=deepcopy(inputs["florida_property_tax"]);down["scenarios"]["Downside"]["rolls"]["buyer"]={}
        with self.assertRaisesRegex(ValueError,"buyer:2034:just_value"):
            fiscal.fiscal_cash(down,inputs["holding_tax_cash"],"Downside",self.calendar("Downside"))

    def test_school_non_school_cap_reset_and_quarter_boundaries_remain_distinct(self):
        inputs=self.spec["rent_inputs"]
        taxes,_,_=fiscal.fiscal_cash(inputs["florida_property_tax"],inputs["holding_tax_cash"],"Downside",self.calendar("Downside"))
        before=taxes["preopening-quarter-1"]["rolls"][0]
        self.assertEqual(value(before["cap"]),Q(5,100))
        self.assertEqual(value(before["non_school_assessed_value"]),1575000)
        self.assertEqual(value(before["school_taxable_value"]),2000000)
        amounts=[value(taxes[f"operation-quarter-{i}"]["total"]) for i in range(1,5)]
        self.assertEqual(amounts,[9750,9750,11050,11050])
        reset=taxes["operation-quarter-3"]["rolls"][0]
        self.assertEqual(reset["assessment_treatment"],"qualifying_improvement_reset")
        self.assertIsNone(reset["cap"])
        self.assertEqual(value(reset["non_school_assessed_value"]),3400000)
        buyer=taxes[FORWARD_PERIOD]["rolls"][-1]
        self.assertEqual(buyer["owner"],"buyer")
        self.assertIsNone(buyer["cap"])
        self.assertEqual(value(buyer["non_school_assessed_value"]),5500000)

    def test_missing_rates_sources_and_budget_scope_never_become_zero(self):
        inputs=self.spec["rent_inputs"]
        for bad in (None,""):
            for key in ("school_mills","non_school_mills","source_ref"):
                raw=deepcopy(inputs["florida_property_tax"])
                raw["scenarios"]["Base"]["rolls"]["millage"]["2027"][key]=bad
                with self.assertRaises(ValueError):fiscal.fiscal_cash(raw,inputs["holding_tax_cash"],"Base",self.calendar("Base"))
        zero=deepcopy(inputs["florida_property_tax"])
        for rate in zero["scenarios"]["Base"]["rolls"]["millage"].values():
            rate.update(school_mills=rational(0),non_school_mills=rational(0))
        taxes,_,cash=fiscal.fiscal_cash(zero,inputs["holding_tax_cash"],"Base",self.calendar("Base"))
        self.assertTrue(all(value(t["total"])==0 for t in taxes.values()))
        self.assertEqual(value(cash["preopening_tax_total"]),0)
        bad=deepcopy(inputs["holding_tax_cash"]);bad["scenarios"]["Base"]["budget_exclusion_ref"]=None
        with self.assertRaisesRegex(ValueError,"budget_exclusion"):
            fiscal.fiscal_cash(inputs["florida_property_tax"],bad,"Base",self.calendar("Base"))

    def test_pinned_adapter_does_not_mutate_or_replace_archived_horizon(self):
        import worksheet_holding_horizon_D266 as original
        before=(original.PROFILE,deepcopy(original.RULES),original.operation_rows,original.configuration)
        fiscal.functions()
        self.assertEqual((original.PROFILE,original.RULES,original.operation_rows,original.configuration),before)
        with patch.object(fiscal,"BASE_ALGORITHM_SHA256","0"*64):
            with self.assertRaisesRegex(ValueError,"algorithm_revision_unconfirmed"):fiscal.functions()
        self.assertEqual((original.PROFILE,original.RULES,original.operation_rows,original.configuration),before)


class FiscalHorizonIntegrationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        temp=TemporaryDirectory(prefix="miniuw-d267-integrated-");cls.addClassCleanup(temp.cleanup)
        cls.root=Path(temp.name);cls.spec=settings();cls.sources=sources_for(cls.spec,cls.root/"sources");cls.counter=0
        cls.control,cls.saved,cls.directory=cls.probe("control")

    @classmethod
    def probe(cls,label,spec=None):
        cls.counter+=1;path=cls.root/label
        assemble(cls.spec if spec is None else spec,register(cls.sources,f"SYNTHETIC-D267-test-{cls.counter}"),cls.sources,path)
        saved=read_package(path)
        return json.loads(saved["results.json"]),saved,path

    def test_source_based_financial_reconciliation_audit_and_current_pdf(self):
        model=self.control
        self.assertEqual(model["decision"],"PENDING")
        self.assertFalse(model["deployment_enabled"]);self.assertFalse(model["real_decisions_enabled"])
        self.assertEqual(model["critical_evidence_review"]["counts"],dict(VERIFIED_GREEN=116,FALSE_GREEN=0,PENDING=0))
        checked=independently_verify(self.spec,self.sources,model)
        self.assertEqual({v["loan_payments"] for v in checked.values()},{20})
        audited=verify_package(self.directory,current_revision_raw=self.saved[CURRENT_REVISION_FILE])
        self.assertEqual((audited["vigencia"],audited["critical_evidence"]["status"]),("VIGENTE","PASSED"))
        current=self.root/"current.json";current.write_bytes(self.saved[CURRENT_REVISION_FILE])
        output=self.root/"current.pdf"
        deliver_package(self.directory,output,current)
        self.assertEqual(output.read_bytes(),self.saved["MiniUW_Resumen.pdf"])
        from pypdf import PdfReader
        reader=PdfReader(output);self.assertEqual(len(reader.pages),1)
        text=reader.pages[0].extract_text()
        for literal in ("D267","USD 10","Q1,2:","Q3,4:","2033-01-01","2033-07-01","PENDING"):
            self.assertIn(literal,text)

    def test_missing_fiscal_roll_blocks_affected_cash_instead_of_using_proxy(self):
        changed=deepcopy(self.spec)
        changed["rent_inputs"]["florida_property_tax"]["scenarios"]["Downside"]["rolls"]["seller"]["2030"].pop("valuation_ref")
        model,saved,path=self.probe("missing-roll",changed)
        down=model["scenarios"]["Downside"]
        self.assertIsNone(down["cash_per_usd_10"])
        self.assertNotIn("horizon_without_refinance",down)
        self.assertTrue(any("valuation_ref_missing" in reason for reason in down["blockers"]))
        self.assertEqual(cash_values(model["scenarios"]["Base"]["cash_per_usd_10"]),cash_values(self.control["scenarios"]["Base"]["cash_per_usd_10"]))
        current=self.root/"missing-current.json";current.write_bytes(saved[CURRENT_REVISION_FILE])
        with self.assertRaises(ValueError):deliver_package(path,self.root/"missing.pdf",current)
        self.assertFalse((self.root/"missing.pdf").exists())

    def test_a_green_fiscal_claim_with_wrong_detail_withholds_cash_and_delivery(self):
        original=fiscal.fiscal_cash
        def wrong(*args,**kwargs):
            taxes,first,proof=original(*args,**kwargs)
            if args[2]=="Downside":
                proof=deepcopy(proof)
                key="operation-quarter-6";item=proof["audit_windows"][key]
                payload=item["payload"]|dict(non_school_tax=rational(value(item["payload"]["non_school_tax"])+1))
                proof["audit_windows"][key]=item|dict(payload=payload)
            return taxes,first,proof
        with patch.object(fiscal,"fiscal_cash",side_effect=wrong):
            model,saved,path=self.probe("false-fiscal-green")
            self.assertIsNone(model["scenarios"]["Downside"]["cash_per_usd_10"])
            self.assertEqual(model["critical_evidence_review"]["fields"]["Downside:fiscal:operation-quarter-6"]["status"],"FALSE_GREEN")
            current=self.root/"false-current.json";current.write_bytes(saved[CURRENT_REVISION_FILE])
            with self.assertRaisesRegex(ValueError,"Cotejo D219 PENDING"):
                deliver_package(path,self.root/"false-green.pdf",current)
        self.assertFalse((self.root/"false-green.pdf").exists())

    def test_fiscal_reference_cannot_omit_a_quarter_or_all_windows(self):
        for empty in (False,True):
            ref=json.loads(fiscal.REFERENCE.read_bytes())
            if empty:ref["holding_fiscal"]["Downside"]["windows"]={}
            else:ref["holding_fiscal"]["Downside"]["windows"].pop("operation-quarter-6")
            observed=audit(self.control,self.saved,self.saved[CURRENT_REVISION_FILE],ref)
            self.assertEqual(observed["status"],"PENDING")
            self.assertEqual(observed["fields"]["Downside:fiscal:source_inventory"]["status"],"FALSE_GREEN")

    def test_joint_plan_and_dscr_corrections_preserve_cash_and_only_deliver_current(self):
        import worksheet_documented_finance_D147 as docs
        original=docs.review_documents
        def read_fault(plan,dscr):
            def reading(*args,**kwargs):
                review=original(*args,**kwargs)
                if plan:review["bots"]["B06"]["locator"]="p. 99 / wrong plan citation"
                if dscr:review["bots"]["B08"]["bank_pdf_by_scenario"]["Downside"]["locators"].pop("C72")
                return review
            return reading
        for label,plan,dscr in (("both",True,True),("dscr-restored",True,False),("plan-restored",False,True)):
            with patch.object(docs,"review_documents",side_effect=read_fault(plan,dscr)):
                model,saved,path=self.probe(label)
                self.assertIsNone(model["scenarios"]["Downside"]["cash_per_usd_10"])
                if plan:self.assertIsNone(model["scenarios"]["Base"]["cash_per_usd_10"])
                else:self.assertEqual(cash_values(model["scenarios"]["Base"]["cash_per_usd_10"]),cash_values(self.control["scenarios"]["Base"]["cash_per_usd_10"]))
                current=self.root/(label+"-current.json");current.write_bytes(saved[CURRENT_REVISION_FILE])
                with self.assertRaises(ValueError):deliver_package(path,self.root/(label+".pdf"),current)
        model,saved,path=self.probe("restored")
        for name in ("Base","Downside"):
            self.assertEqual(cash_values(model["scenarios"][name]["cash_per_usd_10"]),cash_values(self.control["scenarios"][name]["cash_per_usd_10"]))
        current=self.root/"restored-current.json";current.write_bytes(saved[CURRENT_REVISION_FILE])
        stale=verify_package(self.directory,current_revision_raw=current.read_bytes())
        self.assertEqual((stale["vigencia"],stale["decision"]),("HISTORICO","PENDING"))
        with self.assertRaises(ValueError):deliver_package(self.directory,self.root/"old.pdf",current)
        output=self.root/"restored.pdf";deliver_package(path,output,current)
        self.assertEqual(output.read_bytes(),saved["MiniUW_Resumen.pdf"])

    def test_three_year_fiscal_component_preserves_explicit_zeros_and_final_balloon(self):
        from check_lorena_criteria_D192 import change_cells
        from plan_return_D107 import FORWARD_PERIOD
        from worksheet_project_calendar_D145 import offset
        from datetime import date
        spec=deepcopy(self.spec);spec["schema"]=WORKBOOK_FLORIDA_TAX_SCHEMA
        spec["criteria_revision"]="SYNTHETIC-D267-three-year-zero-criteria"
        inputs=spec["rent_inputs"]
        for name in ("Base","Downside"):
            start=date.fromisoformat(self.control["scenarios"][name]["project_calendar"]["stabilization_date"])
            sale=offset(start,36)
            inputs["holding_horizon"]["scenarios"][name]["holding_months"]=36
            inputs["supplemental_scope"][name]["sale_date"]["value"]=str(sale)
            inputs["permanent_loan"]["scenarios"][name]["maturity_payments"]=12
            inputs["supplemental_scope"][name]["maturity_payments"]["value"]=12
            tax=inputs["florida_property_tax"]["scenarios"][name]
            buyer=deepcopy(tax["rolls"]["buyer"]["2034"]);buyer["event_date"]=str(sale)
            tax["rolls"]["buyer"]={str(sale.year+1):buyer}
            for levy in tax["rolls"]["millage"].values():levy.update(school_mills=rational(0),non_school_mills=rational(0))
            for rule in spec["rules"]:
                if rule["scenario_id"]==name and rule["metric_id"] in ("IRR","equity_multiple","asking_relative_to_supported_price"):
                    rule["period_ref"]=f"2027-04-01/{sale}"
        values={name:dict(C69="0",C60="0",C75="0",C76="0") for name in ("Base","Downside")}
        sources=sources_for(spec,self.root/"zero-sources",cell_changes=values,bank_values={name:dict(C69="0") for name in values})
        path=self.root/"three-year-zero"
        assemble(spec,register(sources,"SYNTHETIC-D267-three-year-zero"),sources,path)
        saved=read_package(path);model=json.loads(saved["results.json"])
        independently_verify(spec,sources,model)
        for view in model["scenarios"].values():
            self.assertFalse(view["blockers"],view["blockers"])
            self.assertEqual(len(view["holding_horizon"]["annual_cash"]),3)
            fiscal=view["holding_horizon"]["fiscal_cash"]
            self.assertEqual(value(fiscal["preopening_tax_total"]),0)
            self.assertEqual(value(fiscal["operating_tax_total"]),0)
            self.assertEqual(value(view["replacement_reserve"]["total_deposited"]),0)
            self.assertTrue(all(value(p["interest_due"])==0 for p in view["permanent_loan"]["projected_schedule"]))
            self.assertGreater(value(view["dated_debt_service"]["balloon_due"]),0)
            self.assertEqual(view["debt_principal_paid_at_sale"],view["dated_debt_service"]["closing_balance"])
        audit=verify_package(path,current_revision_raw=saved[CURRENT_REVISION_FILE])
        self.assertEqual(audit["vigencia"],"VIGENTE")
