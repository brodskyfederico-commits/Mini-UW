"""T23 synthetic project-equity cash story; retained value never becomes a receipt."""
from dataclasses import dataclass
from datetime import date
from fractions import Fraction
from pathlib import Path
import hashlib,json
from .drafts import ContextSeed,ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant
from .debt_service import _fraction,rational
from .operating_noi import _bounded,ArithmeticBudgetError
from .periodic_returns import isolate_periodic_returns,ENGINE_SHA256 as ROOT_ENGINE_SHA256

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SCHEMA='miniuw.synthetic-investor-returns.v1'
CATEGORIES={'contribution':{'initial_capital','additional_capital','refinance_cash_in'},
    'distribution':{'net_refinance_distribution','operating_distribution','net_sale_distribution','other_distribution'}}


def _date(value):
    if type(value)is not str:raise ValidationError('explicit ISO date required')
    try:d=date.fromisoformat(value)
    except ValueError as error:raise ValidationError('invalid date')from error
    if value!=d.isoformat():raise ValidationError('canonical ISO date required')
    return d


def parse_investor_returns(raw):
    if type(raw)is not bytes or not raw or len(raw)>1_048_576:raise ValidationError('bounded synthetic investor source required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid investor JSON')from error
    keys={'schema','context','currency','equity_level','event_inventory_declared_complete','grid','events','normalization','capital_snapshots','annual_cash_bases','irr_parameters'}
    if type(p)is not dict or set(p)!=keys or p['schema']!=SCHEMA or p['equity_level']!='aggregate_project_equity':raise ValidationError('explicit project-equity-only source required; no inferred LP allocation')
    if type(p['context'])is not dict:raise ValidationError('explicit synthetic context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact context required')from error
    nonempty(p['currency'],'currency')
    if p['event_inventory_declared_complete']is not None and type(p['event_inventory_declared_complete'])is not bool:raise ValidationError('explicit event inventory declaration required')
    grid=p['grid']
    if type(grid)is not dict or set(grid)!={'spacing','step_months','dates','timing_basis_ref'}or grid['spacing']!='calendar_months_same_day':raise ValidationError('explicit regular calendar-month grid required')
    if type(grid['step_months'])is not int or not 1<=grid['step_months']<=120:raise ValidationError('bounded positive explicit month step required')
    nonempty(grid['timing_basis_ref'],'timing_basis_ref')
    if type(grid['dates'])is not list or not 2<=len(grid['dates'])<=65:raise ValidationError('two to 65 complete regular points required')
    dates=[_date(x)for x in grid['dates']];start=dates[0]
    for i,d in enumerate(dates):
        month=start.year*12+start.month-1+i*grid['step_months']
        try:expected=date(month//12,month%12+1,start.day)
        except ValueError as error:raise ValidationError('month-end adjustment requires a separate explicit profile')from error
        if d!=expected:raise ValidationError('grid dates disagree with declared equal-month spacing')
    if type(p['events'])is not list or len(p['events'])>256:raise ValidationError('bounded explicit equity event list required')
    ids=set()
    for row in p['events']:
        if type(row)is not dict or set(row)!={'event_id','date','kind','category','amount','currency','source_ref'}:raise ValidationError('exact gross equity event fields required')
        for k in ['event_id','kind','category','currency']:nonempty(row[k],k)
        if row['event_id']in ids:raise ValidationError('duplicate equity event identity')
        ids.add(row['event_id']);_date(row['date']);_fraction(row['amount'])
        if row['kind']not in CATEGORIES or row['category']not in CATEGORIES[row['kind']]:raise ValidationError('only explicitly classified equity contributions/distributions accepted')
        if row['source_ref']is not None:nonempty(row['source_ref'],'source_ref')
    norm=p['normalization']
    if type(norm)is not dict or set(norm)!={'reference_amount','contribution_event_ids','basis_ref'}:raise ValidationError('explicit normalization amount and basis required')
    _fraction(norm['reference_amount'])
    if type(norm['contribution_event_ids'])is not list or any(type(x)is not str or not x for x in norm['contribution_event_ids'])or len(set(norm['contribution_event_ids']))!=len(norm['contribution_event_ids']):raise ValidationError('explicit unique normalization event references required')
    if norm['basis_ref']is not None:nonempty(norm['basis_ref'],'basis_ref')
    for family,keys in [('capital_snapshots',{'as_of_date','capital_still_invested','retained_equity_value','currency','basis_ref','source_ref'}),('annual_cash_bases',{'year','capital_base','currency','basis_ref','source_ref'})]:
        if type(p[family])is not list or len(p[family])>65:raise ValidationError('bounded explicit stock/basis inventory required')
        seen=set()
        for row in p[family]:
            if type(row)is not dict or set(row)!=keys:raise ValidationError('exact stock/basis fields required')
            identity=row['as_of_date']if family=='capital_snapshots'else row['year']
            if family=='capital_snapshots':
                d=_date(identity)
                if not dates[0]<=d<=dates[-1]:raise ValidationError('capital snapshot outside declared horizon')
                _fraction(row['capital_still_invested']);_fraction(row['retained_equity_value'])
            else:
                if type(identity)is not int or not 1<=identity<=9999:raise ValidationError('explicit calendar cash-receipt year required')
                _fraction(row['capital_base'])
            if identity in seen:raise ValidationError('duplicate capital snapshot or annual basis')
            seen.add(identity);nonempty(row['currency'],'currency')
            for k in ['basis_ref','source_ref']:
                if row[k]is not None:nonempty(row[k],k)
    params=p['irr_parameters']
    if type(params)is not dict or set(params)!={'rate_domain','max_periodic_rate_interval_width','split_budget','operation_budget','periods_per_year'}or params['rate_domain']!='r_gt_minus_one_positive_discount_factor':raise ValidationError('explicit periodic IRR domain and controls required')
    w=_fraction(params['max_periodic_rate_interval_width'])
    if w is None or w<=0:raise ValidationError('positive explicit periodic rate interval width required')
    for k,lo,hi in [('split_budget',0,2048),('operation_budget',1,200000)]:
        if type(params[k])is not int or not lo<=params[k]<=hi:raise ValidationError('explicit bounded IRR work control required')
    if params['periods_per_year']is not None and(type(params['periods_per_year'])is not int or not 1<=params['periods_per_year']<=12):raise ValidationError('explicit supported annualization frequency or null required')
    return p


def definition_sources():
    root=Path(__file__).resolve().parents[2];refs=[]
    for path,marker in [('docs/model-hold-exit-returns.md','## Ledger del inversor'),('docs/investor-return-bridges.md','## Caja bruta y neta'),('docs/investor-return-bridges.md','## Anualización condicionada'),('docs/periodic-irr-root-isolation.md','## Método exacto acotado')]:
        raw=(root/path).read_bytes();lines=raw.decode().splitlines();hits=[i+1 for i,line in enumerate(lines)if line.startswith(marker)]
        if len(hits)!=1:raise ValidationError('investor definition locator changed')
        refs.append({'path':path,'line':hits[0],'sha256':hashlib.sha256(raw).hexdigest()})
    return refs


@dataclass(frozen=True)
class InvestorReturnsRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def produce_investor_returns(raw):
    p=parse_investor_returns(raw);refs=definition_sources();cash_blockers=[];story_blockers=[];dates=p['grid']['dates']
    if p['event_inventory_declared_complete']is not True:cash_blockers.append('equity_event_inventory_not_declared_complete')
    events={r['event_id']:r for r in p['events']};amounts={};flows=[Fraction(0)for _ in dates];totalA=totalD=Fraction(0);by_category={k:Fraction(0)for values in CATEGORIES.values()for k in values};annual={}
    # Keep cashless calendar years visible; never compress the holding period.
    annual={year:{'contributions':Fraction(0),'distributions':Fraction(0),'operating_distributions':Fraction(0)}
        for year in range(_date(dates[0]).year,_date(dates[-1]).year+1)}
    valid=not cash_blockers
    try:
        for event in p['events']:
            issues=[];value=_fraction(event['amount'])
            if value is None:issues.append('amount_missing')
            elif value<0:issues.append('gross_amount_negative')
            if event['currency']!=p['currency']:issues.append('currency_mismatch')
            if event['source_ref']is None:issues.append('source_ref_missing')
            if event['date']not in dates:issues.append('date_not_bound_to_regular_grid')
            if issues:valid=False;cash_blockers.extend(event['event_id']+':'+i for i in issues);continue
            amounts[event['event_id']]=value;index=dates.index(event['date']);year=_date(event['date']).year
            row=annual.setdefault(year,{'contributions':Fraction(0),'distributions':Fraction(0),'operating_distributions':Fraction(0)})
            sign=1 if event['kind']=='distribution'else-1
            flows[index]=_bounded(flows[index]+sign*value);by_category[event['category']]=_bounded(by_category[event['category']]+value)
            if sign<0:totalA=_bounded(totalA+value);row['contributions']=_bounded(row['contributions']+value)
            else:
                totalD=_bounded(totalD+value);row['distributions']=_bounded(row['distributions']+value)
                if event['category']=='operating_distribution':row['operating_distributions']=_bounded(row['operating_distributions']+value)
        if not valid:totalA=totalD=None
        profit=_bounded(totalD-totalA)if valid else None
        multiple=_bounded(totalD/totalA)if valid and totalA>0 else None
        if valid and totalA==0:story_blockers.append('equity_multiple_undefined_zero_contributions')
        norm=p['normalization'];basis=Fraction(0);norm_issues=[];ref=_fraction(norm['reference_amount'])
        if ref is None or ref<=0:norm_issues.append('positive_reference_amount_missing')
        if not norm['contribution_event_ids']or norm['basis_ref']is None:norm_issues.append('normalization_basis_missing')
        for eid in norm['contribution_event_ids']:
            if eid not in events or events[eid]['kind']!='contribution':norm_issues.append('normalization_reference_not_a_contribution')
            elif eid not in amounts:norm_issues.append('normalization_amount_unavailable')
            else:basis=_bounded(basis+amounts[eid])
        if basis<=0:norm_issues.append('normalization_basis_not_positive')
        factor=_bounded(ref/basis)if valid and not norm_issues else None
        story_blockers.extend(norm_issues)
        q=lambda x:None if x is None else rational(x)
        normalized_events=[dict(e,amount=q(_bounded(amounts[e['event_id']]*factor)))for e in p['events']]if factor is not None else None
        normalized={'reference_amount':norm['reference_amount'],'basis_event_ids':norm['contribution_event_ids'],'basis_ref':norm['basis_ref'],
            'basis_amount':q(basis),'scale_factor':q(factor),'events':normalized_events,
            'total_contributions':q(_bounded(totalA*factor))if factor is not None else None,'total_distributions':q(_bounded(totalD*factor))if factor is not None else None,
            'net_cash_profit':q(_bounded(profit*factor))if factor is not None else None,'equity_multiple':q(multiple)}
        snapshots=[]
        if not p['capital_snapshots']:story_blockers.append('capital_and_retained_equity_snapshots_missing')
        for s in p['capital_snapshots']:
            issues=[];capital=_fraction(s['capital_still_invested']);equity=_fraction(s['retained_equity_value'])
            if capital is None or capital<0:issues.append('capital_still_invested_missing_or_negative')
            if equity is None:issues.append('retained_equity_value_missing')
            if s['currency']!=p['currency']or s['basis_ref']is None or s['source_ref']is None:issues.append('snapshot_metadata_missing_or_mismatch')
            story_blockers.extend('snapshot:'+s['as_of_date']+':'+i for i in issues)
            snapshots.append(dict(s,retained_value_included_in_receipts=False,
                normalized_capital_still_invested=q(_bounded(capital*factor))if not issues and factor is not None else None,
                normalized_retained_equity_value=q(_bounded(equity*factor))if not issues and factor is not None else None))
        bases={s['year']:s for s in p['annual_cash_bases']};annual_rows=[]
        for year,row in sorted(annual.items()):
            basis_row=bases.get(year);base_value=None if basis_row is None else _fraction(basis_row['capital_base']);coc=None
            if not valid:annual_issue='cash_metrics_blocked'
            elif basis_row is None or base_value is None or base_value<=0:annual_issue='positive_declared_annual_capital_base_missing'
            elif basis_row['currency']!=p['currency']or basis_row['basis_ref']is None or basis_row['source_ref']is None:annual_issue='annual_capital_base_metadata_missing_or_mismatch'
            else:annual_issue=None;coc=_bounded(row['operating_distributions']/base_value)
            if annual_issue:story_blockers.append(str(year)+':'+annual_issue)
            annual_rows.append({'calendar_cash_receipt_year':year,'gross_contributions':q(row['contributions'])if valid else None,
                'gross_distributions':q(row['distributions'])if valid else None,'net_equity_cash':q(_bounded(row['distributions']-row['contributions']))if valid else None,
                'operating_distributions_only':q(row['operating_distributions'])if valid else None,
                'normalized_operating_distributions':q(_bounded(row['operating_distributions']*factor))if factor is not None else None,
                'declared_capital_base':None if basis_row is None else basis_row['capital_base'],'conditional_coc':q(coc),'blocker':annual_issue,
                'operating_year_coverage_financially_verified':False})
        irr=None;annual_roots=[];params=p['irr_parameters']
        if valid:
            irr=isolate_periodic_returns(flows,_fraction(params['max_periodic_rate_interval_width']),params['split_budget'],params['operation_budget'])
            if irr['status']!='complete_synthetic'or irr['distinct_positive_discount_roots']!=1:story_blockers.append('IRR_requires_unique_complete_root_or_explicit_resolution')
            frequency=params['periods_per_year']
            if frequency is None or frequency*p['grid']['step_months']!=12:story_blockers.append('annualization_frequency_missing_or_inconsistent')
            else:
                for root in irr['roots']:
                    def annual_rate(r):return rational(_bounded(_bounded((1+Fraction(r))**frequency)-1))
                    if root['exact_periodic_rate']is not None:annual_roots.append({'exact_annual_rate':annual_rate(root['exact_periodic_rate']),'annual_rate_interval':None})
                    else:
                        interval=root['periodic_rate_interval'];annual_roots.append({'exact_annual_rate':None,'annual_rate_interval':dict(interval,lower=annual_rate(interval['lower']),upper=annual_rate(interval['upper']))})
    except ArithmeticBudgetError:
        valid=False;cash_blockers.append('investor_exact_arithmetic_budget_exceeded');totalA=totalD=profit=multiple=None;normalized=None;snapshots=[];annual_rows=[];irr=None;annual_roots=[]
    payload={'component':'T23-T24','purpose':'synthetic_project_equity_cash_return_story','engine_sha256':ENGINE_SHA256,'root_engine_sha256':ROOT_ENGINE_SHA256,
        'source_sha256':hashlib.sha256(raw).hexdigest(),'definition_sources':refs,'context':p['context'],'currency':p['currency'],'equity_level':p['equity_level'],
        'events':p['events'],'gross_contributions':None if totalA is None else rational(totalA),'gross_distributions':None if totalD is None else rational(totalD),
        'net_cash_profit':None if profit is None else rational(profit),'equity_multiple':None if multiple is None else rational(multiple),
        'cash_by_category':{k:rational(v)for k,v in by_category.items()}if valid else None,
        'dated_net_flows':[{'date':d,'net':rational(v)}for d,v in zip(dates,flows)]if valid else None,
        'normalized_story':normalized,'capital_snapshots':snapshots,'annual_cash_receipts':annual_rows,
        'periodic_irr':irr,'annual_irr_roots':annual_roots,'selected_IRR':None,'cash_blockers':sorted(set(cash_blockers)),
        'story_blockers':sorted(set(story_blockers)),'cash_metrics_state':'computed_synthetic'if valid else'blocked',
        'declared_cash_story_computable':valid and not story_blockers,'investor_story_complete':False,
        'cash_projection_producers_connected':False,'risk_analysis_completed':False,
        'retained_equity_included_in_cash_receipts':False,
        'cash_source_and_scope_financially_verified':False,'cash_horizon':{'start':dates[0],'end':dates[-1],'future_cash_after_horizon_included':False},
        'capital_snapshots_are_declared_not_derived':True,'LP_allocation_applied':False,'investment_criteria_applied':False,
        'decision':'PENDING','run_ready':False,'review_authenticated':False,'production_authorized':False,'financial_module_closed':False}
    encoded=canonical(payload);return InvestorReturnsRun(encoded,digest(encoded))
