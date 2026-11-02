"""T29 synthetic gross-cash closing and explicit residual-to-equity hypothesis.

Obligations/proceeds are supplied dated projections, not verified bank balances.
"""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import hashlib,json
from .drafts import ContextSeed,ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant
from .investor_returns import _date
from .debt_service import _fraction,rational
from .operating_noi import _bounded,ArithmeticBudgetError

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SCHEMA='miniuw.synthetic-closing-cash.v1'
DUE=('principal','interest','fees','other')
CASH_FIELDS=('gross_proceeds','reserve_release','new_reserve','closing_costs_paid','other_cash_sources','other_cash_uses')
STOCK_FIELDS={'opening_free_cash':'project_cash_before_closing','opening_restricted_cash':'project_cash_before_closing',
    'retained_free_cash':'project_cash_after_closing','closing_restricted_cash_claim':'project_cash_after_closing'}


def parse_closing_cash(raw):
    if type(raw)is not bytes or not raw or len(raw)>1_048_576:raise ValidationError('bounded explicit synthetic closing source required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid closing JSON')from error
    keys={'schema','profile','context','currency','closing_date','kind','representation','debt_inventory_declared_complete',
        'classification_basis_ref','equity_residual_basis_ref','equity_funding_assumption_ref','amounts','old_debts','new_loan','valuation_claim'}
    if type(p)is not dict or set(p)!=keys or p['schema']!=SCHEMA or p['profile']!='SYNTHETIC-RESIDUAL-AFTER-EXPLICIT-RETENTION-v1':raise ValidationError('exact explicit residual projection profile required')
    if p['kind']not in {'refinance','sale'}:raise ValidationError('explicit refinance or sale closing required')
    if type(p['context'])is not dict:raise ValidationError('synthetic context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact synthetic context required')from error
    nonempty(p['currency'],'currency');_date(p['closing_date']);nonempty(p['representation'],'representation')
    if p['debt_inventory_declared_complete']is not None and type(p['debt_inventory_declared_complete'])is not bool:raise ValidationError('explicit debt inventory declaration or null required')
    for key in ['classification_basis_ref','equity_residual_basis_ref','equity_funding_assumption_ref']:
        if p[key]is not None:nonempty(p[key],key)
    def amount(row):
        if type(row)is not dict or set(row)!={'value','currency','as_of_date','basis','source_ref'}:raise ValidationError('exact dated monetary claim required')
        _fraction(row['value'])
        for key in ['currency','basis','source_ref']:
            if row[key]is not None:nonempty(row[key],key)
        if row['as_of_date']is not None:_date(row['as_of_date'])
    if type(p['amounts'])is not dict or set(p['amounts'])!=set(CASH_FIELDS)|set(STOCK_FIELDS):raise ValidationError('all gross cash/retention claims including zero required')
    for row in p['amounts'].values():amount(row)
    if type(p['old_debts'])is not list or len(p['old_debts'])>64:raise ValidationError('bounded explicit old-debt inventory required')
    ids=set()
    for debt in p['old_debts']:
        if type(debt)is not dict or set(debt)!={'loan_id'}|{kind+'_'+suffix for kind in DUE for suffix in ['due','paid']}:raise ValidationError('all old debt obligations and payments required')
        nonempty(debt['loan_id'],'loan_id')
        if debt['loan_id']in ids:raise ValidationError('duplicate old debt identity')
        ids.add(debt['loan_id'])
        for key,row in debt.items():
            if key!='loan_id':amount(row)
    new=p['new_loan']
    if p['kind']=='sale':
        if new is not None:raise ValidationError('new-loan proceeds require a separate sale-with-financing profile')
    else:
        if type(new)is not dict or set(new)!={'loan_id','principal_after_closing'}:raise ValidationError('explicit new refinance loan required')
        nonempty(new['loan_id'],'loan_id')
        if new['loan_id']in ids:raise ValidationError('new loan must be distinct from old debts')
        amount(new['principal_after_closing'])
    if p['valuation_claim']is not None:amount(p['valuation_claim'])
    return p


def definition_sources():
    root=Path(__file__).resolve().parents[2];refs=[]
    for path,marker in [('docs/operating-settlement-bridges.md','## Estado de cierre y ledger'),('docs/operating-settlement-bridges.md','## Deuda, valorización y representación'),('docs/model-refinance-contract.md','## Puente de caja del evento de refinanciación')]:
        raw=(root/path).read_bytes();hits=[i+1 for i,line in enumerate(raw.decode().splitlines())if line.startswith(marker)]
        if len(hits)!=1:raise ValidationError('closing definition locator changed')
        refs.append({'path':path,'line':hits[0],'sha256':hashlib.sha256(raw).hexdigest()})
    return refs


@dataclass(frozen=True)
class ClosingCashRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def produce_closing_cash(raw):
    s=parse_closing_cash(raw);refs=definition_sources();blockers=[];lineage=[];debts=[];values={};payoffs={k:Fraction(0)for k in DUE};payoff_available={k:True for k in DUE}
    if s['representation']!='explicit_gross_cash_movements':blockers.append('net_or_withheld_cash_requires_counterpart_profile_no_gross_cash_invented')
    if s['debt_inventory_declared_complete']is not True:blockers.append('old_debt_and_obligation_inventory_not_declared_complete')
    if s['classification_basis_ref']is None:blockers.append('cash_and_debt_classification_basis_missing')
    def amount(row,locator,basis):
        bad=[];value=_fraction(row['value'])
        if value is None:bad.append('amount_missing')
        elif value<0:bad.append('negative_gross_amount_unsupported')
        if row['currency']!=s['currency']:bad.append('currency_missing_or_mismatch')
        if row['as_of_date']!=s['closing_date']:bad.append('closing_cutoff_missing_or_mismatch')
        if row['basis']!=basis:bad.append('basis_missing_or_mismatch')
        if row['source_ref']is None:bad.append('source_reference_missing')
        blockers.extend(locator+':'+b for b in bad);lineage.append({'locator':locator,'declared_claim':row,'blockers':bad})
        return None if bad else value
    residual=distribution=contribution=restricted=restricted_residual=conservation=new_principal=None
    exportD=exportA=None
    try:
        for key in CASH_FIELDS:values[key]=amount(s['amounts'][key],'/amounts/'+key,'cash_flow_at_closing')
        for key,basis in STOCK_FIELDS.items():values[key]=amount(s['amounts'][key],'/amounts/'+key,basis)
        for index,debt in enumerate(s['old_debts']):
            results={}
            for category in DUE:
                due=amount(debt[category+'_due'],f'/old_debts/{index}/{category}_due','debt_obligation_before_closing')
                paid=amount(debt[category+'_paid'],f'/old_debts/{index}/{category}_paid','cash_flow_at_closing')
                remaining=None if due is None or paid is None else _bounded(due-paid)
                if remaining is not None and remaining!=0:blockers.append(debt['loan_id']+':'+category+':projected_obligation_not_exactly_closed')
                if paid is not None:payoffs[category]=_bounded(payoffs[category]+paid)
                else:payoff_available[category]=False
                results[category]={'due':None if due is None else rational(due),'paid':None if paid is None else rational(paid),'projected_remaining':None if remaining is None else rational(remaining)}
            debts.append({'loan_id':debt['loan_id'],'obligations':results})
        if s['kind']=='refinance':
            new_principal=amount(s['new_loan']['principal_after_closing'],'/new_loan/principal_after_closing','debt_principal_after_closing')
            if new_principal is not None and values['gross_proceeds']is not None and new_principal!=values['gross_proceeds']:blockers.append('new_principal_vs_gross_draw_mismatch_non_cash_or_withheld_adjustment_needs_other_profile')
        if not blockers:
            payoff=Fraction(0)
            for v in payoffs.values():payoff=_bounded(payoff+v)
            restricted=_bounded(values['opening_restricted_cash']+values['new_reserve']-values['reserve_release'])
            restricted_residual=_bounded(values['closing_restricted_cash_claim']-restricted)
            residual=_bounded(values['opening_free_cash']+values['gross_proceeds']+values['reserve_release']+values['other_cash_sources']-payoff-values['closing_costs_paid']-values['new_reserve']-values['other_cash_uses']-values['retained_free_cash'])
            if restricted<0:blockers.append('negative_projected_restricted_cash_no_automatic_reserve_funding')
            if restricted_residual!=0:blockers.append('closing_restricted_cash_claim_mismatch')
            if s['equity_residual_basis_ref']is None:blockers.append('residual_to_equity_hypothesis_basis_missing')
            else:
                distribution=max(residual,Fraction(0));contribution=max(-residual,Fraction(0))
                if contribution>0 and s['equity_funding_assumption_ref']is None:blockers.append('cash_in_required_but_projected_equity_funding_assumption_missing')
                conservation=_bounded(values['opening_free_cash']+values['opening_restricted_cash']+values['gross_proceeds']+values['other_cash_sources']+contribution-payoff-values['closing_costs_paid']-values['other_cash_uses']-distribution-values['retained_free_cash']-values['closing_restricted_cash_claim'])
                if conservation!=0:blockers.append('closing_total_cash_conservation_mismatch')
                if not blockers:exportD=distribution;exportA=contribution
    except ArithmeticBudgetError:
        blockers.append('closing_exact_arithmetic_budget_exceeded');residual=distribution=contribution=restricted=restricted_residual=conservation=None;exportD=exportA=None
        payoff_available={k:False for k in DUE}
    q=lambda v:None if v is None else rational(v)
    p={'component':'T29','purpose':'conditional_synthetic_gross_closing_residual','engine_sha256':ENGINE_SHA256,'source_sha256':hashlib.sha256(raw).hexdigest(),
        'definition_sources':refs,'context':s['context'],'currency':s['currency'],'closing_date':s['closing_date'],'kind':s['kind'],
        'old_debt_obligations':debts,'payoff_totals':{k:q(v)if payoff_available[k]else None for k,v in payoffs.items()},'new_loan_principal':q(new_principal),
        'net_residual_after_retention':q(residual),'projected_equity_distribution':q(distribution),'projected_equity_contribution_required':q(contribution),
        'expected_closing_restricted_cash':q(restricted),'restricted_cash_claim_residual':q(restricted_residual),'total_cash_conservation_residual':q(conservation),
        'exportable_equity_distribution':q(exportD),'exportable_equity_contribution':q(exportA),
        'valuation_claim':s['valuation_claim'],'valuation_included_in_cash':False,'lineage':lineage,'blockers':sorted(set(blockers)),
        'state':'computed_synthetic_closing'if exportD is not None else'blocked',
        'obligations_are_supplied_dated_claims':True,'contractual_amortization_or_payoff_verified':False,'actual_debt_discharge_verified':False,
        'cash_movements_actually_paid_verified':False,'debt_inventory_financially_verified':False,'equity_residual_rule_adopted':False,
        'equity_funding_available_verified':False,'distribution_authorized':False,'financial_module_closed':False,
        'decision':'PENDING','run_ready':False,'production_authorized':False}
    encoded=canonical(p);return ClosingCashRun(encoded,digest(encoded))
