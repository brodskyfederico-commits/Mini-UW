"""T68 exact staged simple-interval cash interest for supplied nonrevolving draws."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import hashlib,json
from .drafts import ContextSeed,ValidationError,canonical,digest,nonempty
from .preopening_cash import _object,_claim
from .investor_returns import _date
from .debt_service import _fraction,rational
from .operating_noi import _bounded,ArithmeticBudgetError

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T68-T69.md'


def parse_construction_draws(raw):
    p=_object(raw);keys={'schema','profile','context','currency','loan_id','start_date','end_date','maturity_date','inventory_declared_complete','zero_opening_principal_basis_ref','nonrevolving_commitment_basis_ref','principal_commitment','draw_fee_fraction','periods'}
    if type(p)is not dict or set(p)!=keys or p['schema']!='miniuw.synthetic-construction-draws.v1'or p['profile']!='SYNTHETIC-START-DRAW-END-REPAY-SIMPLE-INTERVAL-NONREVOLVING-v1':raise ValidationError('exact staged simple-interval nonrevolving profile required')
    if type(p['context'])is not dict:raise ValidationError('explicit synthetic context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact synthetic context required')from error
    for key in ['currency','loan_id']:nonempty(p[key],key)
    if not _date(p['start_date'])<_date(p['end_date']):raise ValidationError('positive declared draw horizon required')
    _date(p['maturity_date'])
    if p['inventory_declared_complete']is not None and type(p['inventory_declared_complete'])is not bool:raise ValidationError('explicit inventory declaration or null required')
    for key in ['zero_opening_principal_basis_ref','nonrevolving_commitment_basis_ref']:
        if p[key]is not None:nonempty(p[key],key)
    _claim(p['principal_commitment'])
    def rate(row,interval=False):
        keys={'value','unit','source_ref'}|({'interval_ref'}if interval else set())
        if type(row)is not dict or set(row)!=keys:raise ValidationError('exact rate fraction and source metadata required')
        _fraction(row['value'])
        for key in keys-{'value'}:
            if row[key]is not None:nonempty(row[key],key)
    rate(p['draw_fee_fraction'])
    if type(p['periods'])is not list or not 1<=len(p['periods'])<=128:raise ValidationError('one to 128 explicit draw periods required')
    seen=set()
    for row in p['periods']:
        if type(row)is not dict or set(row)!={'period_id','start_date','end_date','interval_basis_ref','draw_at_start','available_new_draw','principal_repayment_at_end','interest_fraction'}:raise ValidationError('exact draw period required')
        nonempty(row['period_id'],'period_id')
        if row['period_id']in seen:raise ValidationError('duplicate draw period identity')
        seen.add(row['period_id'])
        if not _date(row['start_date'])<_date(row['end_date']):raise ValidationError('positive draw interval required')
        if row['interval_basis_ref']is not None:nonempty(row['interval_basis_ref'],'interval_basis_ref')
        for key in ['draw_at_start','available_new_draw','principal_repayment_at_end']:_claim(row[key])
        rate(row['interest_fraction'],True)
    return p


@dataclass(frozen=True)
class ConstructionDrawRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def produce_construction_draws(raw):
    p=parse_construction_draws(raw);blockers=[];rows=[];exports=None;totals=None
    if p['inventory_declared_complete']is not True:blockers.append('construction_draw_inventory_not_declared_complete')
    for key in ['zero_opening_principal_basis_ref','nonrevolving_commitment_basis_ref']:
        if p[key]is None:blockers.append(key+'_missing')
    if p['end_date']>p['maturity_date']:blockers.append('schedule_past_maturity_no_extension_inferred')
    if p['periods'][0]['start_date']!=p['start_date']or p['periods'][-1]['end_date']!=p['end_date']:blockers.append('draw_intervals_do_not_cover_exact_horizon')
    for a,b in zip(p['periods'],p['periods'][1:]):
        if a['end_date']!=b['start_date']:blockers.append('draw_interval_gap_overlap_or_wrong_order')
    def number(row,path,unit=None,interval=None):
        value=_fraction(row['value'])
        if value is None:blockers.append(path+':value_missing')
        elif value<0:blockers.append(path+':nonnegative_value_required')
        if row['source_ref']is None:blockers.append(path+':source_ref_missing')
        if unit is None:
            if row['currency']!=p['currency']:blockers.append(path+':currency_mismatch')
        elif row['unit']!=unit:blockers.append(path+':unit_mismatch_no_annual_conversion')
        if interval is not None and row['interval_ref']!=interval:blockers.append(path+':interval_ref_mismatch')
        return value
    commitment=number(p['principal_commitment'],'/principal_commitment');fee_rate=number(p['draw_fee_fraction'],'/draw_fee_fraction','gross_draw_fraction');values=[]
    for i,row in enumerate(p['periods']):
        path='/periods/'+str(i)
        if row['interval_basis_ref']is None:blockers.append(path+':interval_basis_missing')
        values.append(tuple(number(row[k],path+'/'+k)for k in ['draw_at_start','available_new_draw','principal_repayment_at_end'])+(number(row['interest_fraction'],path+'/interest_fraction','simple_interval_fraction',row['period_id']),))
    if not blockers:
        try:
            balance=drawn=interest_total=fee_total=repaid=Fraction(0)
            for i,(source,values_row)in enumerate(zip(p['periods'],values)):
                draw,available,repayment,rate=values_row;opening=balance;exposure=_bounded(opening+draw);drawn=_bounded(drawn+draw)
                interest=_bounded(exposure*rate);fee=_bounded(draw*fee_rate);balance=_bounded(exposure-repayment);interest_total=_bounded(interest_total+interest);fee_total=_bounded(fee_total+fee);repaid=_bounded(repaid+repayment)
                if draw>available:blockers.append(source['period_id']+':draw_exceeds_declared_available_new_draw')
                if drawn>commitment:blockers.append(source['period_id']+':cumulative_gross_draws_exceed_nonrevolving_commitment')
                if repayment>exposure:blockers.append(source['period_id']+':repayment_exceeds_principal_after_start_draw')
                rows.append(dict(period_id=source['period_id'],start_date=source['start_date'],end_date=source['end_date'],opening_principal=rational(opening),draw_at_start=rational(draw),interest_exposure=rational(exposure),
                    interest_due_at_end=rational(interest),fee_due_at_start=rational(fee),principal_repayment_at_end=rational(repayment),closing_principal=rational(balance),cumulative_gross_draws=rational(drawn)))
                # Stop after an invalid principal path instead of carrying a negative balance into later interest.
                if balance<0:break
            if p['end_date']==p['maturity_date']and balance!=0:blockers.append('matured_principal_not_repaid_in_declared_schedule')
            if not blockers:
                totals=dict(gross_draws=rational(drawn),principal_repaid=rational(repaid),interest_due=rational(interest_total),fees_due=rational(fee_total),terminal_principal=rational(balance));exports=[]
                for i,row in enumerate(rows):
                    for category,key,date in [('loan_draw','draw_at_start','start_date'),('debt_fee_payment','fee_due_at_start','start_date'),('debt_interest_payment','interest_due_at_end','end_date'),('loan_principal_repayment','principal_repayment_at_end','end_date')]:
                        exports.append(dict(loan_id=p['loan_id'],period_id=row['period_id'],category=category,date=row[date],amount=row[key],currency=p['currency'],source_pointer='/periods/'+str(i)+'/'+key))
        except ArithmeticBudgetError:blockers.append('construction_draw_exact_arithmetic_budget_exceeded');rows=[];totals=None;exports=None
    result={'component':'T68','purpose':'synthetic_supplied_nonrevolving_construction_draw_interest','engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),
        'source_sha256':hashlib.sha256(raw).hexdigest(),'context':p['context'],'currency':p['currency'],'loan_id':p['loan_id'],'start_date':p['start_date'],'end_date':p['end_date'],'maturity_date':p['maturity_date'],
        'periods':rows,'totals':totals,'exportable_proposed_debt_cash_events':exports,'blockers':sorted(set(blockers)),'state':'computed_synthetic_construction_draw_plan'if exports is not None else'blocked',
        'annual_rate_or_day_count_conversion_applied':False,'commitment_restored_by_repayment':False,'capitalized_interest_supported':False,'automatic_draws_or_equity_generated':False,
        'actual_bank_funding_payments_or_credit_verified':False,'investment_policy_adopted':False,'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return ConstructionDrawRun(encoded,digest(encoded))
