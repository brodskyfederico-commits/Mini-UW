"""Verify the five-year worksheet, independent cash reference and PENDING gates."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))

from check_lorena_criteria_D192 import change_cells
from check_unified_worksheet_D48 import call
from check_worksheet_holding_horizon_D266 import independently_verify,settings,sources_for,evidence_bundle
from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE,encoded,read_package,verify_package
from test_worksheet_exact_cash import cash_values
from test_worksheet_integrated_transport import numeric_cells
from worksheet_holding_horizon_D266 import CALENDAR_RULES,configuration,horizon_calendar,amount,verify_rows
from worksheet_intake_D198 import assemble,register
from worksheet_project_calendar_D145 import offset
from datetime import date


class HoldingHorizonContractTests(TestCase):
    def test_duration_source_and_zero_are_explicit(self):
        raw=settings()["rent_inputs"]["holding_horizon"]
        self.assertEqual(configuration(raw,"Base")["holding_months"],60)
        self.assertEqual(amount(configuration(raw,"Base")["without_refinance"]["fee_at_stabilization"]["value"]),0)
        for value in (None,0,"60",True,13,72):
            changed=deepcopy(raw)
            changed["scenarios"]["Base"]["holding_months"]=value
            with self.assertRaises(ValueError):configuration(changed,"Base")
        changed=deepcopy(raw)
        changed["scenarios"]["Base"]["initial_equity"]["value"]=None
        with self.assertRaises(ValueError):configuration(changed,"Base")
        changed=deepcopy(raw)
        changed["scenarios"]["Base"]["cash_assumptions_ref"]=""
        with self.assertRaises(ValueError):configuration(changed,"Base")

    def test_calendar_measures_from_stabilization_and_rejects_unfunded_gap_or_wrong_sale(self):
        spec=settings()["rent_inputs"]
        review=dict(workbook_sha256="a"*64,rows=[dict(value_cell=f"Inputs!{cell}",value=rational(value),
            state="CONFIRMED_SYNTHETIC") for cell,value in (("C46",6),("C47",3))])
        purchase="2027-04-01"
        scope=spec["supplemental_scope"]["Base"]["sale_date"]
        cal=horizon_calendar(spec["project_calendar"],"Base",review,purchase,scope,spec["holding_horizon"])
        self.assertEqual((cal["stabilization_date"],cal["sale_date"]),("2028-01-01","2033-01-01"))
        self.assertEqual(len([d for d in cal["equity_dates"] if cal["stabilization_date"]<d<=cal["sale_date"]]),20)
        wrong=scope|dict(value="2032-10-01")
        with self.assertRaisesRegex(ValueError,"sale_date_must_match"):
            horizon_calendar(spec["project_calendar"],"Base",review,purchase,wrong,spec["holding_horizon"])
        delayed=deepcopy(spec["project_calendar"])
        delayed["scenarios"]["Base"]["tco_date"]="2028-01-01"
        with self.assertRaisesRegex(ValueError,"tco_conflicts"):
            horizon_calendar(delayed,"Base",review,purchase,scope,spec["holding_horizon"])

    def test_cash_conservation_checks_each_row_and_between_rows(self):
        row=dict(date="2028-01-01",stage="operation",opening_free=Fraction(),opening_restricted=Fraction(),
            sources=Fraction(10),uses=Fraction(8),closing_free=Fraction(1),closing_restricted=Fraction(1),
            contribution=Fraction(),distribution=Fraction(8))
        verify_rows([row])
        with self.assertRaisesRegex(ValueError,"conservation"):
            verify_rows([row|dict(uses=Fraction(7))])
        next_row=row|dict(date="2028-04-01",opening_free=Fraction(1),closing_free=Fraction(2))
        with self.assertRaisesRegex(ValueError,"discontinuity"):
            verify_rows([row,next_row])


class HoldingHorizonIntegrationTests(TestCase):
    def test_five_year_intake_independent_reference_replay_missing_capacity_and_maturity(self):
        with TemporaryDirectory(prefix="miniuw-d266-test-") as temporary:
            root=Path(temporary)
            spec=settings()
            sources=sources_for(spec,root/"sources")
            counter=0
            def probe(label,config=None,data=None):
                nonlocal counter
                counter+=1
                cfg=spec if config is None else config
                raw=sources if data is None else data
                path=root/label
                assemble(cfg,register(raw,f"SYNTHETIC-D266-test-{counter}"),raw,path)
                saved=read_package(path)
                return json.loads(saved["results.json"]),saved,path
            before=deepcopy(spec)
            complete,saved,package=probe("complete")
            self.assertEqual(spec,before)
            self.assertEqual(complete["decision"],"PENDING")
            self.assertFalse(complete["deployment_enabled"])
            self.assertFalse(complete["real_decisions_enabled"])
            self.assertFalse(complete["local_review"]["blockers"])
            checked=independently_verify(spec,sources,complete)
            self.assertEqual({v["loan_payments"] for v in checked.values()},{20})
            self.assertEqual(complete["simulation_result"],"PENDING")
            self.assertEqual(complete["screening"]["simulation_blockers"],["intermediate_band_pending_professional_review"])
            for name,view in complete["scenarios"].items():
                self.assertEqual(len(view["holding_horizon"]["annual_cash"]),5)
                self.assertEqual(len(view["holding_horizon"]["annual_noi"]),5)
                self.assertEqual(len(view["holding_horizon"]["operating_aggregate"]["noi_source"]["income_rows"]),5)
                self.assertFalse(view["post_refinance_coc"]["blockers"])
                self.assertIsNotNone(complete["screening"]["irr_by_scenario"][name]["annual_enclosure"])
                self.assertEqual(amount(view["replacement_reserve"]["total_deposited"]),5*amount(view["replacement_reserve"]["deposit"]))
            self.assertEqual(verify_package(package,current_revision_raw=saved[CURRENT_REVISION_FILE])["vigencia"],"VIGENTE")
            current=root/"current.json"
            current.write_bytes(saved[CURRENT_REVISION_FILE])
            exported=root/"MiniUW_Vigente.pdf"
            delivered=call("deliver",package,"--current-revision",current,"--output",exported)
            self.assertEqual(delivered["pdf_sha256"],sha(exported.read_bytes()))
            self.assertEqual(exported.read_bytes(),saved["MiniUW_Resumen.pdf"])

            missing=deepcopy(spec)
            missing["rent_inputs"]["holding_horizon"]["scenarios"]["Downside"].pop("holding_months")
            blocked,_,_=probe("missing-duration",missing)
            self.assertIsNone(blocked["scenarios"]["Downside"]["cash_per_usd_10"])
            self.assertEqual(cash_values(blocked["scenarios"]["Base"]["cash_per_usd_10"]),cash_values(complete["scenarios"]["Base"]["cash_per_usd_10"]))

            no_growth=dict(sources,downside_workbook_raw=numeric_cells(sources["downside_workbook_raw"],{"C75":None}))
            blocked,_,_=probe("missing-growth",data=no_growth)
            self.assertIsNone(blocked["scenarios"]["Downside"]["cash_per_usd_10"])
            self.assertEqual(blocked["decision"],"PENDING")

            no_criterion=dict(sources,criteria_raw=change_cells(sources["criteria_raw"],{"E7":""}))
            pending,_,_=probe("missing-criterion",data=no_criterion)
            self.assertEqual(pending["simulation_result"],"PENDING")
            for n in ("Base","Downside"):
                self.assertEqual(cash_values(pending["scenarios"][n]["cash_per_usd_10"]),cash_values(complete["scenarios"][n]["cash_per_usd_10"]))

            mismatched=dict(sources,downside_workbook_raw=numeric_cells(sources["downside_workbook_raw"],{"C69":"0.066"}))
            pending,_,_=probe("mismatched-quote",data=mismatched)
            self.assertIsNone(pending["scenarios"]["Downside"]["cash_per_usd_10"])
            self.assertTrue(any("bank" in b for b in pending["scenarios"]["Downside"]["blockers"]))

            high_dscr=deepcopy(spec)
            raw=dict(sources,downside_workbook_raw=numeric_cells(sources["downside_workbook_raw"],{"C72":"100"}))
            raw["evidence_raw"]=evidence_bundle(high_dscr,{"Downside":{"C72":"100"}})
            for n in ("Base","Downside"):
                high_dscr["rent_inputs"]["bank_debt_yield"][n]["quote_source_sha256"]=sha(raw["evidence_raw"])
            limited,_,_=probe("capacity",high_dscr,raw)
            down=limited["scenarios"]["Downside"]
            self.assertIsNone(down["cash_per_usd_10"])
            self.assertIn("selected_principal_exceeds_declared_bank_capacity",down["blockers"])
            self.assertIsNotNone(down["horizon_without_refinance"]["cash_per_usd_10"])
            self.assertEqual(cash_values(down["horizon_without_refinance"]["cash_per_usd_10"]),cash_values(complete["scenarios"]["Downside"]["horizon_without_refinance"]["cash_per_usd_10"]))

            short=deepcopy(spec)
            short["rent_inputs"]["permanent_loan"]["scenarios"]["Downside"]["maturity_payments"]=16
            short["rent_inputs"]["supplemental_scope"]["Downside"]["maturity_payments"]["value"]=16
            raw=dict(sources,evidence_raw=evidence_bundle(short))
            for n in ("Base","Downside"):
                short["rent_inputs"]["bank_debt_yield"][n]["quote_source_sha256"]=sha(raw["evidence_raw"])
            early,_,_=probe("early-permanent-maturity",short,raw)
            down=early["scenarios"]["Downside"]
            self.assertIn("holding_permanent_loan_matures_before_horizon_sale",down["blockers"])
            self.assertIsNone(down["cash_per_usd_10"])
            self.assertIsNotNone(down["horizon_without_refinance"]["cash_per_usd_10"])

            short=deepcopy(spec)
            short["rent_inputs"]["construction_financing"]["scenarios"]["Downside"]["maturity_date"]="2030-04-01"
            raw=dict(sources,evidence_raw=evidence_bundle(short))
            for n in ("Base","Downside"):
                short["rent_inputs"]["bank_debt_yield"][n]["quote_source_sha256"]=sha(raw["evidence_raw"])
            early,_,_=probe("early-construction-maturity",short,raw)
            down=early["scenarios"]["Downside"]
            self.assertEqual(cash_values(down["cash_per_usd_10"]),cash_values(complete["scenarios"]["Downside"]["cash_per_usd_10"]))
            self.assertIsNone(down["horizon_without_refinance"]["cash_per_usd_10"])
            self.assertIn("holding_construction_loan_matures_before_sale_without_refinance",down["horizon_without_refinance"]["blockers"])

            # A changed source/registration cannot be delivered using the earlier revision.
            newer_revision=read_package(root/"capacity")[CURRENT_REVISION_FILE]
            history=verify_package(package,current_revision_raw=newer_revision)
            self.assertEqual((history["vigencia"],history["simulation_result"],history["decision"]),("HISTORICO","PENDING","PENDING"))
            current.write_bytes(newer_revision)
            denied=call("deliver",package,"--current-revision",current,"--output",root/"stale.pdf",blocked=True)
            self.assertEqual(denied["decision"],"PENDING")
            self.assertFalse((root/"stale.pdf").exists())
            current.write_bytes(saved[CURRENT_REVISION_FILE])
            final=root/"only-current.pdf"
            call("deliver",package,"--current-revision",current,"--output",final)
            self.assertEqual(final.read_bytes(),saved["MiniUW_Resumen.pdf"])

    def test_zero_rates_and_reserve_shorter_horizon_and_last_payment_maturity(self):
        with TemporaryDirectory(prefix="miniuw-d266-zero-") as temporary:
            root=Path(temporary)
            spec=settings()
            values={n:dict(C69="0",C60="0",C75="0",C76="0") for n in ("Base","Downside")}
            sources=sources_for(spec,root/"sources",cell_changes=values,bank_values={n:dict(C69="0") for n in values})
            assemble(spec,register(sources,"SYNTHETIC-D266-zero"),sources,root/"zero")
            zero=json.loads((root/"zero/results.json").read_bytes())
            independently_verify(spec,sources,zero)
            for view in zero["scenarios"].values():
                self.assertEqual(amount(view["replacement_reserve"]["total_deposited"]),0)
                self.assertTrue(all(amount(r["interest_due"])==0 for r in view["permanent_loan"]["projected_schedule"]))
                self.assertEqual(len({amount(y["noi"]) for y in view["holding_horizon"]["annual_cash"]}),1)
            for name in ("Base","Downside"):
                config=spec["rent_inputs"]
                config["holding_horizon"]["scenarios"][name]["holding_months"]=36
                start=date.fromisoformat(zero["scenarios"][name]["project_calendar"]["stabilization_date"])
                sale=offset(start,36)
                config["supplemental_scope"][name]["sale_date"]["value"]=str(sale)
                config["buyer_forward_property_tax"][name].update(window_start=str(sale),window_end=str(offset(sale,12)))
                config["permanent_loan"]["scenarios"][name]["maturity_payments"]=12
                config["supplemental_scope"][name]["maturity_payments"]["value"]=12
                for rule in spec["rules"]:
                    if rule["scenario_id"]==name and rule["metric_id"] in ("IRR","equity_multiple","asking_relative_to_supported_price"):
                        rule["period_ref"]=f"2027-04-01/{sale}"
            spec["criteria_revision"]="SYNTHETIC-D266-three-year-criteria"
            sources["criteria_raw"]=change_cells(sources["criteria_raw"],{"B18":spec["criteria_revision"]})
            sources["evidence_raw"]=evidence_bundle(spec,{n:dict(C69="0") for n in values})
            for n in values:spec["rent_inputs"]["bank_debt_yield"][n]["quote_source_sha256"]=sha(sources["evidence_raw"])
            assemble(spec,register(sources,"SYNTHETIC-D266-three-year-last-payment"),sources,root/"three")
            three=json.loads((root/"three/results.json").read_bytes())
            independently_verify(spec,sources,three)
            for view in three["scenarios"].values():
                self.assertEqual(len(view["holding_horizon"]["annual_cash"]),3)
                self.assertGreater(amount(view["dated_debt_service"]["balloon_due"]),0)
                self.assertEqual(amount(view["debt_principal_paid_at_sale"]),amount(view["dated_debt_service"]["closing_balance"]))

    def test_long_exact_fractions_and_operating_capital_calls_are_kept_gross(self):
        with TemporaryDirectory(prefix="miniuw-d266-exact-") as temporary:
            root=Path(temporary)
            spec=settings()
            sources=sources_for(spec,root/"sources",cell_changes={"Base":{"C69":"0.0501"}},bank_values={"Base":{"C69":"0.0501"}})
            assemble(spec,register(sources,"SYNTHETIC-D266-long-fractions"),sources,root/"precision")
            precise=json.loads((root/"precision/results.json").read_bytes())
            independently_verify(spec,sources,precise)
            self.assertGreater(len(precise["scenarios"]["Base"]["debt_principal_paid_at_sale"]["denominator"]),256)
            stressed=dict(sources,workbook_raw=numeric_cells(sources["workbook_raw"],{"C60":"60000"}))
            assemble(spec,register(stressed,"SYNTHETIC-D266-operating-calls"),stressed,root/"stressed")
            result=json.loads((root/"stressed/results.json").read_bytes())
            base=result["scenarios"]["Base"]
            self.assertFalse(base["blockers"],base["blockers"])
            cash=base["cash_per_usd_10"]
            calls=[r for r in base["holding_horizon"]["cash_by_period"] if r["stage"]=="operation" and amount(r["contribution"])>0]
            self.assertEqual(len(calls),20)
            self.assertEqual(amount(cash["events"][0]["amount"]),10)
            self.assertEqual(amount(cash["basis_amount"]),2400000)
            self.assertGreater(amount(cash["total_contributions"]),amount(precise["scenarios"]["Base"]["cash_per_usd_10"]["total_contributions"]))
            self.assertTrue(all(amount(r["distribution"])==0 for r in calls))
            self.assertEqual(amount(base["replacement_reserve"]["total_deposited"]),5*60000*26)
            self.assertEqual(amount(cash["total_contributions"]),sum(amount(e["amount"]) for e in cash["events"] if e["kind"]=="contribution"))
            self.assertEqual(amount(cash["unrecovered_after_sale"]),max(Fraction(),amount(cash["total_contributions"])-amount(cash["total_distributions"])))

    def test_declared_initial_equity_changes_the_basis_without_becoming_a_default(self):
        with TemporaryDirectory(prefix="miniuw-d266-initial-") as temporary:
            root=Path(temporary)
            spec=settings()
            sources=sources_for(spec,root/"sources")
            for initial in (1200000,1500000,9000000):
                revised=deepcopy(spec)
                for name in ("Base","Downside"):
                    revised["rent_inputs"]["holding_horizon"]["scenarios"][name]["initial_equity"]=dict(
                        value=rational(initial),source_ref=f"SYNTHETIC-D266-declared-initial-{initial}-{name}")
                path=root/str(initial)
                assemble(revised,register(sources,f"SYNTHETIC-D266-initial-{initial}"),sources,path)
                result=json.loads((path/"results.json").read_bytes())
                if initial==1200000:
                    self.assertIsNone(result["scenarios"]["Downside"]["cash_per_usd_10"])
                    self.assertIn("development_costs_outside_declared_equity_schedule",result["scenarios"]["Downside"]["blockers"])
                    self.assertEqual(amount(result["scenarios"]["Base"]["cash_per_usd_10"]["basis_amount"]),initial)
                    continue
                independently_verify(revised,sources,result)
                for name,view in result["scenarios"].items():
                    self.assertFalse(view["blockers"],view["blockers"])
                    for route in (view,view["horizon_without_refinance"]):
                        cash=route["cash_per_usd_10"]
                        self.assertEqual(amount(cash["basis_amount"]),initial)
                        self.assertEqual(amount(cash["events"][0]["amount"]),10)
                    first=view["construction_financing"]["cash_by_date"][0]
                    self.assertEqual(amount(first["equity_contribution"]),initial)
                    if initial==9000000:
                        self.assertEqual(amount(view["cash_per_usd_10"]["total_contributions"]),10)
                        self.assertGreater(amount(view["construction_financing"]["free_cash_at_refinance"]),0)
