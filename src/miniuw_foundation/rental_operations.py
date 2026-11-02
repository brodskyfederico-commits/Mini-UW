"""T21 explicit synthetic residential-rent and operating-expense producer."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import hashlib,json
from .drafts import ContextSeed,ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant
from .debt_service import _fraction,rational
from .operating_noi import _bounded,ArithmeticBudgetError

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SCHEMA='miniuw.synthetic-residential-operations.v1'
GROUP_KEYS={'group_id','units','unit_rentable_sf','rent','rent_basis','rent_definition','loss_fraction','concession_fraction','concession_basis','currency','source_ref','policy_ref'}
EXPENSE_KEYS={'item_id','kind','rate','currency','source_ref','policy_ref'}


def parse_rental_operations(raw):
    if type(raw)is not bytes or not raw or len(raw)>1_048_576:raise ValidationError('bounded synthetic residential source required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid residential JSON')from error
    if type(p)is not dict or set(p)!={'schema','context','currency','period_ref','months_in_period','months_per_year','residential_groups','expense_items'}or p['schema']!=SCHEMA:raise ValidationError('exact residential profile required')
    if type(p['context'])is not dict:raise ValidationError('explicit context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact synthetic context required')from error
    for k in ['currency','period_ref']:
        if p[k]is not None:nonempty(p[k],k)
    for k in ['months_in_period','months_per_year']:
        if p[k]is not None and type(p[k])is not int:raise ValidationError('explicit integer month counts or null required')
    ids=set()
    for family,keys,identity in [('residential_groups',GROUP_KEYS,'group_id'),('expense_items',EXPENSE_KEYS,'item_id')]:
        if type(p[family])is not list or len(p[family])>64:raise ValidationError('bounded explicit inventory required')
        for row in p[family]:
            if type(row)is not dict or set(row)!=keys:raise ValidationError('exact residential/expense fields required')
            nonempty(row[identity],identity)
            if row[identity]in ids:raise ValidationError('duplicate economic item identity')
            ids.add(row[identity])
            numeric={'units','unit_rentable_sf','rent','loss_fraction','concession_fraction'}if family=='residential_groups'else{'rate'}
            for k in numeric:_fraction(row[k])
            for k in keys-numeric-{identity}:
                if row[k]is not None:nonempty(row[k],k)
    return p


def definition_sources():
    path='docs/model-operations-contract.md';raw=(Path(__file__).resolve().parents[2]/path).read_bytes();lines=raw.decode().splitlines();refs=[]
    for marker in ['| M2-01 |','| M2-02 |','| M2-03 |','| M2-05 |']:
        hits=[i+1 for i,l in enumerate(lines)if l.startswith(marker)]
        if len(hits)!=1:raise ValidationError('residential definition locator changed')
        refs.append({'path':path,'line':hits[0],'sha256':hashlib.sha256(raw).hexdigest()})
    return refs


@dataclass(frozen=True)
class RentalOperationsRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def produce_rental_operations(raw):
    p=parse_rental_operations(raw);refs=definition_sources();blockers=[];groups=[];expenses=[]
    months=p['months_in_period'];year=p['months_per_year']
    month_ok=months is not None and 1<=months<=1200
    if not month_ok:blockers.append('months_in_period_missing_or_outside_profile')
    if year!=12:blockers.append('explicit_regular_12_month_year_required')
    if p['currency']is None:blockers.append('currency_missing')
    if p['period_ref']is None:blockers.append('period_ref_missing')
    if not p['residential_groups']:blockers.append('residential_inventory_empty_not_assumed_zero')
    if not p['expense_items']:blockers.append('expense_inventory_empty_not_assumed_zero')
    gross_total=effective_total=unit_total=Fraction(0);rent_complete=month_ok and year==12 and p['currency']is not None and p['period_ref']is not None and bool(p['residential_groups'])
    try:
        for i,row in enumerate(p['residential_groups']):
            issues=[];n=_fraction(row['units']);area=_fraction(row['unit_rentable_sf']);rate=_fraction(row['rent']);loss=_fraction(row['loss_fraction']);con=_fraction(row['concession_fraction'])
            for key,value in [('units',n),('rent',rate),('loss_fraction',loss),('concession_fraction',con)]:
                if value is None:issues.append(key+'_missing')
            if n is not None and(n<0 or n.denominator!=1):issues.append('unit_count_outside_integer_nonnegative_profile')
            if rate is not None and rate<0:issues.append('rent_outside_nonnegative_profile')
            for key,value in [('loss_fraction',loss),('concession_fraction',con)]:
                if value is not None and not 0<=value<=1:issues.append(key+'_outside_unit_interval')
            if row['currency']is None or row['currency']!=p['currency']:issues.append('currency_missing_or_mismatch')
            if row['source_ref']is None:issues.append('source_ref_missing')
            if row['policy_ref']is None:issues.append('policy_ref_missing')
            if row['rent_basis']not in ['per_unit_per_month','per_rentable_sf_per_month']:issues.append('rent_basis_missing_or_unsupported')
            if row['rent_basis']=='per_rentable_sf_per_month'and(area is None or area<0):issues.append('rentable_area_missing_or_outside_profile')
            if row['rent_definition']=='net_of_concessions':
                if row['concession_basis']!='already_in_rent'or con!=0:issues.append('net_rent_requires_explicit_zero_concession_already_in_rent')
            elif row['rent_definition']=='gross_before_losses_and_concessions':
                if row['concession_basis']not in ['gross_potential_rent','after_vacancy_rent']:issues.append('concession_basis_missing_or_unsupported')
            else:issues.append('rent_definition_missing_or_unsupported')
            values={'gross_potential':None,'vacancy_loss':None,'concession_loss':None,'effective_rent':None}
            if not issues and month_ok and year==12 and p['currency']is not None and p['period_ref']is not None:
                unit_rent=rate if row['rent_basis']=='per_unit_per_month'else _bounded(rate*area)
                gross=_bounded(_bounded(n*unit_rent)*months);vacancy=_bounded(gross*loss);after=_bounded(gross-vacancy)
                concession=Fraction(0)if row['concession_basis']=='already_in_rent'else _bounded((gross if row['concession_basis']=='gross_potential_rent'else after)*con)
                effective=_bounded(after-concession)
                values={k:rational(v)for k,v in [('gross_potential',gross),('vacancy_loss',vacancy),('concession_loss',concession),('effective_rent',effective)]}
                gross_total=_bounded(gross_total+gross);effective_total=_bounded(effective_total+effective);unit_total=_bounded(unit_total+n)
            else:rent_complete=False
            blockers.extend('/residential_groups/'+str(i)+':'+reason for reason in issues)
            groups.append({'group_id':row['group_id'],'locator':'/residential_groups/'+str(i),'source_ref':row['source_ref'],'policy_ref':row['policy_ref'],'results':values,'blockers':issues})
        for i,row in enumerate(p['expense_items']):
            issues=[];rate=_fraction(row['rate']);value=None
            if rate is None:issues.append('expense_rate_missing')
            elif rate<0:issues.append('expense_rate_outside_nonnegative_profile')
            if row['currency']is None or row['currency']!=p['currency']:issues.append('currency_missing_or_mismatch')
            if row['source_ref']is None:issues.append('source_ref_missing')
            if row['policy_ref']is None:issues.append('policy_ref_missing')
            if row['kind']not in ['fixed_per_declared_period','per_unit_per_regular_year','fraction_of_residential_effective_rent']:issues.append('expense_kind_missing_or_unsupported')
            if row['kind']=='fraction_of_residential_effective_rent'and rate is not None and rate>1:issues.append('expense_fraction_outside_unit_interval')
            if row['kind']!='fixed_per_declared_period'and not rent_complete:issues.append('required_residential_producer_blocked')
            if not issues and month_ok and year==12 and p['currency']is not None and p['period_ref']is not None:
                value=rate if row['kind']=='fixed_per_declared_period'else(_bounded(_bounded(rate*unit_total)*Fraction(months,year))if row['kind']=='per_unit_per_regular_year'else _bounded(rate*effective_total))
            blockers.extend('/expense_items/'+str(i)+':'+reason for reason in issues)
            expenses.append({'item_id':row['item_id'],'locator':'/expense_items/'+str(i),'source_ref':row['source_ref'],'policy_ref':row['policy_ref'],'kind':row['kind'],'amount':None if value is None else rational(value),'blockers':issues})
    except ArithmeticBudgetError:
        blockers.append('exact_arithmetic_budget_exceeded');rent_complete=False
    expense_complete=len(expenses)==len(p['expense_items'])and bool(expenses)and all(r['amount']is not None for r in expenses)
    expense_total=None
    try:
        if expense_complete:
            expense_total=Fraction(0)
            for row in expenses:expense_total=_bounded(expense_total+_fraction(row['amount'],1300))
    except ArithmeticBudgetError:expense_total=None;blockers.append('exact_arithmetic_budget_exceeded')
    q=lambda v:None if v is None else rational(v)
    payload={'component':'T21','purpose':'synthetic_residential_operations_only','engine_sha256':ENGINE_SHA256,
        'source_sha256':hashlib.sha256(raw).hexdigest(),'definition_sources':refs,'context':p['context'],'currency':p['currency'],'period_ref':p['period_ref'],
        'months_in_period':months,'months_per_year':year,'groups':groups,'expenses':expenses,
        'unit_total':q(unit_total)if rent_complete else None,'gross_potential_total':q(gross_total)if rent_complete else None,
        'residential_effective_rent':q(effective_total)if rent_complete else None,'operating_expenses_excluding_tax':q(expense_total),
        'blockers':sorted(set(blockers)),'state':'computed_synthetic'if not blockers and rent_complete and expense_complete else'blocked',
        'income_scope':'residential_rent_only_excludes_other_and_commercial_income','expense_scope':'explicit_items_only_excludes_property_tax',
        'calendar_verified':False,'economic_scope_verified':False,'rental_policy_adopted':False,'cash_collected_verified':False,
        'decision':'PENDING','run_ready':False,'review_authenticated':False,'production_authorized':False}
    encoded=canonical(payload);return RentalOperationsRun(encoded,digest(encoded))
