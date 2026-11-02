import copy,json,tempfile,unittest
from dataclasses import replace
from pathlib import Path
from fractions import Fraction as F
from unittest.mock import patch
from miniuw_foundation.drafts import ValidationError,canonical,digest
from miniuw_foundation.debt_service import rational as q
from miniuw_foundation.closing_cash import produce_closing_cash,parse_closing_cash,definition_sources
from miniuw_foundation.archive import EvidenceArchive,CorruptArchive,UnsupportedArchive,MissingEvidence
R=Path(__file__).resolve().parents[1]
def raw(p):return canonical(p).encode()
def f(q):return F(int(q['numerator']),int(q['denominator']))
def num(n):return q(F(n))


class ClosingCashTests(unittest.TestCase):
    def setUp(self):self.refi=json.loads((R/'templates/synthetic-refinance-closing.json').read_bytes());self.sale=json.loads((R/'templates/synthetic-sale-closing.json').read_bytes())
    def run_case(self,p=None):return produce_closing_cash(raw(self.refi if p is None else p))
    def test_refinance_distribution_and_conservation_by_hand(self):
        p=self.run_case().payload;self.assertEqual(p['state'],'computed_synthetic_closing')
        self.assertEqual(f(p['net_residual_after_retention']),100+1600+50-1000-50-10-20-100-70)
        self.assertEqual(f(p['exportable_equity_distribution']),500);self.assertEqual(f(p['exportable_equity_contribution']),0)
        self.assertEqual(f(p['expected_closing_restricted_cash']),100);self.assertEqual(f(p['new_loan_principal']),1600);self.assertEqual(f(p['total_cash_conservation_residual']),0)
    def test_sale_net_receipt_after_all_supplied_payoffs(self):
        p=self.run_case(self.sale).payload;self.assertEqual(f(p['exportable_equity_distribution']),70+2400+100-1600-20-10-40)
        self.assertEqual(f(p['exportable_equity_distribution']),900);self.assertIsNone(p['new_loan_principal']);self.assertEqual(f(p['expected_closing_restricted_cash']),0)
    def test_property_value_never_becomes_cash_proceeds(self):
        before=self.run_case().payload;self.refi['valuation_claim']['value']=num(9999999);after=self.run_case().payload
        self.assertEqual(before['net_residual_after_retention'],after['net_residual_after_retention']);self.assertFalse(after['valuation_included_in_cash'])
        self.refi['valuation_claim']=None;self.assertEqual(self.run_case().payload['exportable_equity_distribution'],before['exportable_equity_distribution'])
    def test_retention_and_restricted_transfer_not_double_counted_as_returns(self):
        self.refi['amounts']['retained_free_cash']['value']=num(100);p=self.run_case().payload;self.assertEqual(f(p['exportable_equity_distribution']),470)
        self.refi['amounts']['new_reserve']['value']=num(120);self.refi['amounts']['closing_restricted_cash_claim']['value']=num(120)
        p=self.run_case().payload;self.assertEqual(f(p['exportable_equity_distribution']),450);self.assertEqual(f(p['total_cash_conservation_residual']),0)
    def test_shortfall_is_requirement_and_blocks_without_explicit_funding_assumption(self):
        self.refi['amounts']['gross_proceeds']['value']=num(900);self.refi['new_loan']['principal_after_closing']['value']=num(900)
        p=self.run_case().payload;self.assertEqual(f(p['net_residual_after_retention']),-200);self.assertEqual(f(p['projected_equity_distribution']),0)
        self.assertEqual(f(p['projected_equity_contribution_required']),200);self.assertIsNone(p['exportable_equity_contribution']);self.assertEqual(p['state'],'blocked')
        self.refi['equity_funding_assumption_ref']='SYNTHETIC-explicit-unverified-funding-hypothesis';p=self.run_case().payload
        self.assertEqual(f(p['exportable_equity_contribution']),200);self.assertFalse(p['equity_funding_available_verified']);self.assertEqual(p['decision'],'PENDING')
    def test_zero_residual_preserved_without_fake_cash_in(self):
        self.refi['amounts']['retained_free_cash']['value']=num(570);p=self.run_case().payload
        self.assertEqual(f(p['exportable_equity_distribution']),0);self.assertEqual(f(p['exportable_equity_contribution']),0)
    def test_every_old_obligation_must_be_exactly_settled_in_the_projection(self):
        for category in ['principal','interest','fees','other']:
            p=copy.deepcopy(self.refi);p['old_debts'][0][category+'_paid']['value']=num(0)
            if category=='other':p['old_debts'][0]['other_due']['value']=num(1)
            out=self.run_case(p).payload;self.assertEqual(out['state'],'blocked');self.assertIsNone(out['exportable_equity_distribution'])
            self.assertTrue(any(category+':projected_obligation_not_exactly_closed'in b for b in out['blockers']))
    def test_overpayment_is_not_a_negative_remaining_debt(self):
        self.refi['old_debts'][0]['principal_paid']['value']=num(1001);p=self.run_case().payload
        self.assertEqual(f(p['old_debt_obligations'][0]['obligations']['principal']['projected_remaining']),-1);self.assertIsNone(p['exportable_equity_distribution'])
    def test_missing_due_or_payment_never_assumed_zero(self):
        for key in ['other_due','other_paid','interest_due','fees_paid']:
            p=copy.deepcopy(self.refi);p['old_debts'][0][key]['value']=None;out=self.run_case(p).payload
            self.assertIsNone(out['net_residual_after_retention']);self.assertEqual(out['state'],'blocked')
            if key.endswith('_paid'):self.assertIsNone(out['payoff_totals'][key[:-5]])
    def test_all_old_loans_count_and_duplicate_ids_rejected(self):
        extra=copy.deepcopy(self.refi['old_debts'][0]);extra['loan_id']='SYNTHETIC-other-loan'
        for key,row in extra.items():
            if key!='loan_id':row['value']=num(0)
        extra['other_due']['value']=extra['other_paid']['value']=num(5);self.refi['old_debts'].append(extra)
        self.assertEqual(f(self.run_case().payload['exportable_equity_distribution']),495)
        self.refi['old_debts'].append(copy.deepcopy(extra))
        with self.assertRaises(ValidationError):self.run_case()
    def test_empty_debt_inventory_is_explicit_not_proof_of_debt_freedom(self):
        self.sale['old_debts']=[];p=self.run_case(self.sale).payload;self.assertEqual(f(p['exportable_equity_distribution']),2530)
        self.assertFalse(p['debt_inventory_financially_verified']);self.sale['debt_inventory_declared_complete']=None;self.assertEqual(self.run_case(self.sale).payload['state'],'blocked')
    def test_missing_declarations_classification_and_equity_rule_block(self):
        for key,value in [('debt_inventory_declared_complete',None),('debt_inventory_declared_complete',False),('classification_basis_ref',None),('equity_residual_basis_ref',None)]:
            p=copy.deepcopy(self.refi);p[key]=value;out=self.run_case(p).payload;self.assertEqual(out['state'],'blocked');self.assertIsNone(out['exportable_equity_distribution'])
    def test_net_withheld_escrow_representation_never_invents_gross_movements(self):
        self.refi['representation']='net_withheld_proceeds';p=self.run_case().payload
        self.assertEqual(p['state'],'blocked');self.assertIsNone(p['projected_equity_distribution']);self.assertEqual(self.refi['amounts']['gross_proceeds']['value'],num(1600))
    def test_new_principal_and_gross_proceeds_discrepancy_requires_other_profile(self):
        self.refi['new_loan']['principal_after_closing']['value']=num(1620);p=self.run_case().payload;self.assertEqual(p['state'],'blocked');self.assertIsNone(p['exportable_equity_distribution'])
        self.refi['new_loan']['loan_id']=self.refi['old_debts'][0]['loan_id']
        with self.assertRaises(ValidationError):self.run_case()
        self.sale['new_loan']=copy.deepcopy(self.refi['new_loan'])
        with self.assertRaises(ValidationError):self.run_case(self.sale)
    def test_restricted_cash_never_released_beyond_explicit_available_stock(self):
        self.refi['amounts']['reserve_release']['value']=num(151);p=self.run_case().payload
        self.assertEqual(f(p['expected_closing_restricted_cash']),-1);self.assertIsNone(p['exportable_equity_distribution'])
        self.refi['amounts']['reserve_release']['value']=num(50);self.refi['amounts']['closing_restricted_cash_claim']['value']=num(99)
        self.assertIn('closing_restricted_cash_claim_mismatch',self.run_case().payload['blockers'])
    def test_amount_source_currency_date_basis_negative_and_null_guards(self):
        for field,value in [('value',None),('value',num(-1)),('currency','EUR'),('as_of_date','2028-01-02'),('basis','valuation_not_cash'),('source_ref',None)]:
            p=copy.deepcopy(self.refi);p['amounts']['closing_costs_paid'][field]=value;self.assertEqual(self.run_case(p).payload['state'],'blocked')
    def test_strict_schema_live_context_and_numeric_types_rejected(self):
        for mutate in [lambda p:p['context'].update(deal_id='real-deal'),lambda p:p.update(profile='approved_policy'),lambda p:p['amounts']['other_cash_uses'].update(value=0.0),lambda p:p['old_debts'][0].pop('other_due')]:
            p=copy.deepcopy(self.refi);mutate(p)
            with self.assertRaises(ValidationError):self.run_case(p)
    def test_arithmetic_budget_does_not_export_partial_obligations(self):
        self.refi['old_debts']=[]
        for index,d in enumerate([2**845,3**535,5**365,7**301,11**244,13**229]):
            debt=copy.deepcopy(self.sale['old_debts'][0]);debt['loan_id']='SYNTHETIC-rational-'+str(index)
            for key,row in debt.items():
                if key!='loan_id':row['as_of_date']=self.refi['closing_date'];row['value']=num(0)
            debt['other_due']['value']=debt['other_paid']['value']=q(F(1,d));self.refi['old_debts'].append(debt)
        p=self.run_case().payload;self.assertIn('closing_exact_arithmetic_budget_exceeded',p['blockers']);self.assertIsNone(p['exportable_equity_distribution']);self.assertIsNone(p['payoff_totals']['other'])
    def test_payload_source_and_definitions_are_immutable_and_bound(self):
        r=self.run_case();p=r.payload;p['projected_equity_distribution']=num(999)
        self.assertEqual(f(r.payload['projected_equity_distribution']),500);self.assertEqual(r.sha256,digest(r.payload_json))
        for ref in definition_sources():self.assertEqual(__import__('hashlib').sha256((R/ref['path']).read_bytes()).hexdigest(),ref['sha256'])
    def test_reopened_archive_retains_original_source_and_exact_retry(self):
        source=raw(self.refi);r=self.run_case()
        with tempfile.TemporaryDirectory()as t:
            path=Path(t)/'closing.sqlite3'
            with EvidenceArchive(path)as a:key=a.save_closing_cash(source,r);self.assertEqual(key,a.save_closing_cash(source,r))
            with EvidenceArchive(path)as a:
                b=a.load_closing_cash(key);self.assertEqual(b.run,r);self.assertEqual(a.get_closing_cash_source(b.payload['source_sha256']),source)
    def test_archive_rollback_rehashed_forgery_version_and_missing_source(self):
        source=raw(self.refi);r=self.run_case();p=r.payload;p['exportable_equity_distribution']=num(999);enc=canonical(p);fake=replace(r,payload_json=enc,sha256=digest(enc))
        with EvidenceArchive(':memory:')as a:
            with self.assertRaises(ValidationError):a.save_closing_cash(source,fake)
            with patch.object(a,'_commit',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError):a.save_closing_cash(source,r)
            self.assertEqual(a._connection.execute('SELECT COUNT(*) FROM objects').fetchone()[0],0)
            key=a.save_closing_cash(source,r);body=json.loads(a.read_bundle_bytes(key));body['run']={'payload_json':enc,'sha256':digest(enc)}
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(CorruptArchive):a.load_closing_cash(bad)
            body=json.loads(a.read_bundle_bytes(key));body['versions'][0]='0'*64
            with a._transaction():bad=a._put('bundle',canonical(body).encode())
            with self.assertRaises(UnsupportedArchive):a.load_closing_cash(bad)
            a._connection.execute('DELETE FROM objects WHERE kind=? AND sha256=?',('source',r.payload['source_sha256']))
            with self.assertRaises(MissingEvidence):a.load_closing_cash(key)
    def test_no_residual_policy_bank_payoff_or_funding_authority_adopted(self):
        p=self.run_case().payload;self.assertEqual(p['decision'],'PENDING')
        for key in ['contractual_amortization_or_payoff_verified','actual_debt_discharge_verified','cash_movements_actually_paid_verified','debt_inventory_financially_verified','equity_residual_rule_adopted','equity_funding_available_verified','distribution_authorized','financial_module_closed','run_ready','production_authorized']:self.assertFalse(p[key])
