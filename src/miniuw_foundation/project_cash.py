"""T33 declared cash window: operations -> refinance -> operations -> sale.

Reduced exact-boundary profile; not historical construction or actual bank evidence.
"""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import hashlib,json,re
from .drafts import ContextSeed,ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant
from .holding_cash import verify_period_evidence,OperatingPeriodEvidence
from .operating_cash import WORKING
from .closing_cash import ClosingCashRun,parse_closing_cash
from .debt_closing import DatedLoanEvidence,DebtClosingRun,reconcile_debt_closing
from .debt_service import _fraction,rational,parse_loan_terms
from .operating_noi import _bounded,ArithmeticBudgetError
from .investor_returns import _date
ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SCHEMA='miniuw.synthetic-project-cash.v1'


@dataclass(frozen=True,kw_only=True)
class CheckedClosingEvidence:
    closing_id:str
    closing_raw:bytes
    closing_run:ClosingCashRun
    loans:tuple[DatedLoanEvidence,...]
    debt_spec_raw:bytes
    debt_run:DebtClosingRun
    def __post_init__(self):
        nonempty(self.closing_id,'closing_id')
        if type(self.closing_raw)is not bytes or type(self.debt_spec_raw)is not bytes or type(self.closing_run)is not ClosingCashRun or type(self.debt_run)is not DebtClosingRun or type(self.loans)is not tuple or len(self.loans)>64 or any(type(e)is not DatedLoanEvidence for e in self.loans):raise ValidationError('immutable complete debt-checked closing evidence required')


def parse_project_cash(raw):
    if type(raw)is not bytes or not raw or len(raw)>1_048_576:raise ValidationError('bounded explicit cash-window manifest required')
    try:m=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid cash-window JSON')from error
    keys={'schema','profile','context','currency','opening_date','terminal_date','scope_inventory_declared_complete','opening_state_basis_ref','timeline_basis_ref','refinance_working_balance_carry_basis_ref','nodes'}
    if type(m)is not dict or set(m)!=keys or m['schema']!=SCHEMA or m['profile']!='SYNTHETIC-OPERATIONS-REFINANCE-SALE-CONTINUITY-v1':raise ValidationError('exact operating/refinance/terminal-sale profile required')
    if type(m['context'])is not dict:raise ValidationError('explicit synthetic context required')
    try:ContextSeed(**m['context'])
    except TypeError as error:raise ValidationError('exact context required')from error
    nonempty(m['currency'],'currency')
    if not _date(m['opening_date'])<_date(m['terminal_date']):raise ValidationError('positive declared cash-window horizon required')
    if m['scope_inventory_declared_complete']is not None and type(m['scope_inventory_declared_complete'])is not bool:raise ValidationError('explicit scope declaration or null required')
    for key in ['opening_state_basis_ref','timeline_basis_ref','refinance_working_balance_carry_basis_ref']:
        if m[key]is not None:nonempty(m[key],key)
    if type(m['nodes'])is not list or not 4<=len(m['nodes'])<=65:raise ValidationError('four to 65 explicit ordered cash nodes required')
    seen=set()
    for row in m['nodes']:
        if type(row)is not dict or set(row)!={'node_id','kind','source_sha256','run_sha256','upstream_source_sha256','upstream_run_sha256'}:raise ValidationError('exact node source/upstream identity required')
        nonempty(row['node_id'],'node_id')
        if row['node_id']in seen:raise ValidationError('duplicate cash-node identity')
        seen.add(row['node_id'])
        if type(row['kind'])is not str or row['kind']not in {'operation','refinance','sale'}:raise ValidationError('explicit supported node kind required')
        for key in ['source_sha256','run_sha256','upstream_source_sha256','upstream_run_sha256']:
            if type(row[key])is not str or not re.fullmatch('[a-f0-9]{64}',row[key]):raise ValidationError('exact source/run SHA-256 required')
    return m


def verify_project_sources(periods,closings):
    if type(closings)is not tuple or len(closings)>64 or any(type(c)is not CheckedClosingEvidence for c in closings):raise ValidationError('bounded immutable closing inventory required')
    if type(periods)is not tuple or len(periods)>65 or any(type(p)is not OperatingPeriodEvidence for p in periods):raise ValidationError('bounded immutable period inventory required')
    size=sum(len(p.noi_raw)+len(p.spec_raw)for p in periods)+sum(len(c.closing_raw)+len(c.debt_spec_raw)+sum(len(e.loan_raw)for e in c.loans)for c in closings)
    if size>8_388_608:raise ValidationError('complete project source transport budget exceeded')
    operating=verify_period_evidence(periods);sources={}
    for key,(e,s)in operating.items():sources[key]={'kind':'operation','e':e,'spec':s,'run':e.cash_run.payload,'source_sha256':hashlib.sha256(e.spec_raw).hexdigest(),'run_sha256':e.cash_run.sha256,'upstream_source_sha256':hashlib.sha256(e.noi_raw).hexdigest(),'upstream_run_sha256':e.noi_run.sha256}
    for e in closings:
        if e.closing_id in sources:raise ValidationError('duplicate or colliding closing identity')
        if reconcile_debt_closing(e.loans,e.closing_raw,e.closing_run,e.debt_spec_raw)!=e.debt_run:raise ValidationError('every closing, loan and cutoff source must reproduce, including extras')
        s=parse_closing_cash(e.closing_raw);sources[e.closing_id]={'kind':s['kind'],'e':e,'spec':s,'run':e.closing_run.payload,'source_sha256':hashlib.sha256(e.closing_raw).hexdigest(),'run_sha256':e.closing_run.sha256,'upstream_source_sha256':hashlib.sha256(e.debt_spec_raw).hexdigest(),'upstream_run_sha256':e.debt_run.sha256}
    return sources


def definition_sources():
    root=Path(__file__).resolve().parents[2];refs=[]
    for path,marker in [('docs/operating-settlement-bridges.md','## Operación devengada y caja'),('docs/operating-settlement-bridges.md','## Estado de cierre y ledger'),('docs/model-refinance-contract.md','| M6-07 |'),('docs/model-hold-exit-returns.md','| M7-08 |')]:
        data=(root/path).read_bytes();hits=[i+1 for i,l in enumerate(data.decode().splitlines())if l.startswith(marker)]
        if len(hits)!=1:raise ValidationError('cash-window definition locator changed')
        refs.append({'path':path,'line':hits[0],'sha256':hashlib.sha256(data).hexdigest()})
    return refs


@dataclass(frozen=True)
class ProjectCashRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def reconcile_project_cash(periods,closings,manifest_raw):
    m=parse_project_cash(manifest_raw);sources=verify_project_sources(periods,closings);blockers=[];nodes=[];edges=[];working=[];debt_checks=[];funding_links=[];totals=None;residual=None;exports=None
    expected={n['node_id']for n in m['nodes']}
    for key in sorted(expected-set(sources)):blockers.append(key+':node_evidence_missing')
    for key in sorted(set(sources)-expected):blockers.append(key+':extra_node_evidence_not_in_manifest')
    if m['scope_inventory_declared_complete']is not True:blockers.append('cash_window_inventory_not_declared_complete')
    for key in ['opening_state_basis_ref','timeline_basis_ref','refinance_working_balance_carry_basis_ref']:
        if m[key]is None:blockers.append(key+'_missing')
    kinds=[n['kind']for n in m['nodes']]
    valid_shape=kinds[0]=='operation'and kinds[-1]=='sale'and kinds.count('refinance')==1 and kinds.count('sale')==1
    if valid_shape:
        ri=kinds.index('refinance');valid_shape=ri>0 and ri<len(kinds)-2 and all(k=='operation'for k in kinds[:ri]+kinds[ri+1:-1])
    if not valid_shape:blockers.append('profile_requires_operations_then_one_refinance_then_operations_then_terminal_sale')
    def stock(s,key,date):return {'claim':s['spec']['amounts'][key],'source_sha256':s['source_sha256'],'pointer':'/amounts/'+key,'as_of_date':date}
    for row in m['nodes']:
        key=row['node_id'];s=sources.get(key);local=[];entry={'node_id':key,'kind':row['kind'],'binding_blockers':local,'source_sha256':None if s is None else s['source_sha256'],'run_sha256':None if s is None else s['run_sha256'],'upstream_run_sha256':None if s is None else s['upstream_run_sha256'],'opening':None,'closing':None,'start_date':None,'end_date':None,'equity_cash_date':None,'distribution':None,'contribution':None,'producer_blockers':[]}
        if s is not None:
            r=s['run'];spec=s['spec']
            if row['kind']!=s['kind']:local.append('node_kind_mismatch')
            for field in ['source_sha256','run_sha256','upstream_source_sha256','upstream_run_sha256']:
                if row[field]!=s[field]:local.append(field+'_mismatch')
            if r['context']!=m['context']:local.append('node_context_mismatch')
            if r['currency']!=m['currency']:local.append('node_currency_mismatch')
            if s['kind']=='operation':
                if r['state']!='reconciled_synthetic_plan':local.append('operating_plan_blocked')
                start,end=r['start_date'],r['end_date'];date=r['cash_date'];D=r['exportable_operating_distribution'];A=r['exportable_equity_contribution']
                opening={c:stock(s,'opening_'+c+'_cash',start)for c in ['free','restricted']};closing={c:stock(s,'closing_'+c+'_cash_claim',end)for c in ['free','restricted']}
            else:
                if r['state']!='computed_synthetic_closing'or s['e'].debt_run.payload['state']!='matched_synthetic_debt_assumptions':local.append('debt_checked_closing_blocked')
                start=end=date=r['closing_date'];D=r['exportable_equity_distribution'];A=r['exportable_equity_contribution']
                opening={c:stock(s,'opening_'+c+'_cash',date)for c in ['free','restricted']};closing={'free':stock(s,'retained_free_cash',date),'restricted':stock(s,'closing_restricted_cash_claim',date)}
            entry.update(start_date=start,end_date=end,equity_cash_date=date,opening=opening,closing=closing,distribution=D,contribution=A,producer_blockers=r['blockers']+([]if s['kind']=='operation'else s['e'].debt_run.payload['blockers']))
        entry['valid']=s is not None and not local
        blockers.extend(key+':'+b for b in local);nodes.append(entry)
    if nodes[0]['start_date']!=m['opening_date']:blockers.append('first_operation_does_not_start_at_opening_date')
    if nodes[-1]['end_date']!=m['terminal_date']:blockers.append('sale_does_not_match_terminal_date')
    for previous,current in zip(nodes,nodes[1:]):
        if not previous['valid']or not current['valid']:blockers.append(current['node_id']+':cash_boundary_unverifiable');continue
        if previous['end_date']!=current['start_date']:blockers.append(current['node_id']+':cash_date_gap_overlap_or_reversed_order')
        for account in ['free','restricted']:
            a=previous['closing'][account];b=current['opening'][account];equal=_fraction(a['claim']['value'])==_fraction(b['claim']['value'])
            edges.append({'from_node':previous['node_id'],'to_node':current['node_id'],'account':account,'closing_claim':a,'opening_claim':b,'equal_exact_value':equal})
            if not equal:blockers.append(current['node_id']+':'+account+':opening_cash_does_not_equal_previous_close')
    last_op=None;phase=[];phase_closings=[]
    try:
        for node in nodes:
            s=sources.get(node['node_id'])
            if not node['valid']:continue
            if node['kind']=='operation':
                if last_op is not None:
                    for family in WORKING:
                        a=last_op['spec']['working_balances'][family]['closing'];b=s['spec']['working_balances'][family]['opening'];equal=_fraction(a['value'])==_fraction(b['value'])
                        working.append({'balance':family,'previous_operating_source_sha256':last_op['source_sha256'],'next_operating_source_sha256':s['source_sha256'],'closing_claim':a,'opening_claim':b,'equal_exact_value':equal})
                        if not equal:blockers.append(node['node_id']+':'+family+':working_balance_discontinuity_across_boundary')
                last_op=s;phase.append(s)
            else:
                phase_closings.append(s)
                if not phase:blockers.append(node['node_id']+':operating_phase_missing_before_closing');continue
                if any(row['payment_cutoff']!='before_regular_payment'for row in json.loads(s['e'].debt_spec_raw)['loans']):blockers.append(node['node_id']+':integrated_profile_requires_before_regular_payment_cutoff')
                loan_terms=[(e,parse_loan_terms(e.loan_raw))for e in s['e'].loans]
                for evidence,terms in loan_terms:
                    if terms['origination_date']is None or terms['origination_date']>phase[0]['run']['start_date']:blockers.append(node['node_id']+':loan_originates_inside_operating_phase_without_draw_profile')
                for op in phase:
                    expected_p=expected_i=Fraction(0);selected=[]
                    for evidence,terms in loan_terms:
                        for payment in evidence.run.payload['schedule']:
                            if op['run']['start_date']<=payment['date']<op['run']['end_date']:
                                expected_p=_bounded(expected_p+_fraction(payment['principal_due'],1300));expected_i=_bounded(expected_i+_fraction(payment['interest_due'],1300))
                                selected.append({'loan_id':terms['loan_id'],'payment_index':payment['payment_index'],'date':payment['date']})
                                if _fraction(payment['balloon_due'],1300)!=0:blockers.append(op['spec']['period_ref']+':balloon_inside_operation_requires_separate_cash_profile')
                    amounts=op['spec']['amounts'];P=_fraction(amounts['debt_principal_payment']['value']);I=_fraction(amounts['debt_interest_payment']['value']);fee=_fraction(amounts['debt_fee_payment']['value'])
                    equal=P==expected_p and I==expected_i and fee==0
                    debt_checks.append({'operating_node':op['spec']['period_ref'],'closing_node':node['node_id'],'selected_regular_payments':selected,'computed_principal':rational(expected_p),'computed_interest':rational(expected_i),'claimed_principal':amounts['debt_principal_payment'],'claimed_interest':amounts['debt_interest_payment'],'claimed_fee':amounts['debt_fee_payment'],'equal_with_zero_unmodeled_fee':equal})
                    if not equal:blockers.append(op['spec']['period_ref']+':operating_debt_cash_differs_from_dated_regular_schedule_or_has_unmodeled_fee')
                if node['kind']=='sale'and last_op is not None:
                    for family in WORKING:
                        claim=last_op['spec']['working_balances'][family]['closing']
                        if _fraction(claim['value'])!=0:blockers.append(node['node_id']+':'+family+':terminal_working_balance_requires_explicit_settlement_profile')
                phase=[]
        if valid_shape and len(phase_closings)==2 and all(n['valid']for n in nodes):
            refi,sale=phase_closings;new=refi['spec']['new_loan'];sale_loans={e.run.payload['loan_id']:e for e in sale['e'].loans}
            matched=new is not None and set(sale_loans)=={new['loan_id']}
            if matched:
                terms=parse_loan_terms(sale_loans[new['loan_id']].loan_raw)
                matched=terms['origination_date']==refi['run']['closing_date']and _fraction(terms['principal'])==_fraction(new['principal_after_closing']['value'])
            funding_links.append({'refinance_node':next(n['node_id']for n in nodes if n['kind']=='refinance'),'new_loan_id':None if new is None else new['loan_id'],'sale_loan_inventory_matches_refinance_origin_principal':matched})
            if not matched:blockers.append('sale_debt_does_not_match_refinance_new_loan_origin_and_principal')
        if not blockers:
            totals={k:Fraction(0)for k in ['operating_receipts','operating_payments','other_sources','other_uses','loan_draws','sale_proceeds','debt_principal','debt_interest','debt_fees','debt_other','capex','closing_costs','equity_contributions','equity_distributions','reserve_deposits','reserve_releases']}
            def add(key,value):totals[key]=_bounded(totals[key]+value)
            for node in nodes:
                s=sources[node['node_id']];a=s['spec']['amounts'];r=s['run']
                add('equity_contributions',_fraction(node['contribution'],1300));add('equity_distributions',_fraction(node['distribution'],1300))
                if node['kind']=='operation':
                    add('operating_receipts',_fraction(r['expected_operating_receipts'],1300));add('operating_payments',_fraction(r['expected_operating_payments'],1300))
                    for key,source in [('other_sources','nonfinancing_other_cash_receipt'),('other_uses','other_cash_payment'),('debt_principal','debt_principal_payment'),('debt_interest','debt_interest_payment'),('debt_fees','debt_fee_payment'),('capex','capital_expenditure'),('reserve_deposits','reserve_deposit'),('reserve_releases','reserve_release')]:add(key,_fraction(a[source]['value']))
                else:
                    add('loan_draws'if node['kind']=='refinance'else'sale_proceeds',_fraction(a['gross_proceeds']['value']))
                    for key,source in [('other_sources','other_cash_sources'),('other_uses','other_cash_uses'),('closing_costs','closing_costs_paid'),('reserve_deposits','new_reserve'),('reserve_releases','reserve_release')]:add(key,_fraction(a[source]['value']))
                    for category in ['principal','interest','fees','other']:add('debt_'+category,_fraction(r['payoff_totals'][category],1300))
            for key,node,side,account in [('opening_free_cash',nodes[0],'opening','free'),('opening_restricted_cash',nodes[0],'opening','restricted'),('terminal_free_cash',nodes[-1],'closing','free'),('terminal_restricted_cash',nodes[-1],'closing','restricted')]:totals[key]=_fraction(node[side][account]['claim']['value'])
            residual=_bounded(sum((totals[k]for k in ['opening_free_cash','opening_restricted_cash','operating_receipts','other_sources','loan_draws','sale_proceeds','equity_contributions']),Fraction(0))-sum((totals[k]for k in ['operating_payments','other_uses','debt_principal','debt_interest','debt_fees','debt_other','capex','closing_costs','equity_distributions','terminal_free_cash','terminal_restricted_cash']),Fraction(0)))
            if residual!=0:blockers.append('declared_cash_window_conservation_mismatch')
            else:exports=[{'node_id':n['node_id'],'kind':n['kind'],'date':n['equity_cash_date'],'run_sha256':n['run_sha256'],'distribution':n['distribution'],'contribution':n['contribution']}for n in nodes]
    except ArithmeticBudgetError:blockers.append('project_cash_exact_arithmetic_budget_exceeded');totals=None;residual=None;exports=None
    p={'component':'T33','purpose':'synthetic_operating_refinance_sale_cash_window','engine_sha256':ENGINE_SHA256,'manifest_source_sha256':hashlib.sha256(manifest_raw).hexdigest(),'definition_sources':definition_sources(),
        'context':m['context'],'currency':m['currency'],'opening_date':m['opening_date'],'terminal_date':m['terminal_date'],'nodes':nodes,'cash_boundary_checks':edges,'working_balance_checks':working,'operating_debt_checks':debt_checks,'refinance_to_sale_loan_links':funding_links,
        'totals':None if totals is None else{k:rational(v)for k,v in totals.items()},'cash_conservation_residual':None if residual is None else rational(residual),'exportable_equity_movements':exports,'blockers':sorted(set(blockers)),
        'state':'reconciled_synthetic_cash_window'if exports is not None and not blockers else'blocked','all_supplied_sources_replayed':True,
        'declared_cash_window_reconciled':exports is not None and not blockers,'whole_project_cash_reconciled':False,'historical_construction_and_asset_funding_verified':False,'actual_cash_and_payment_history_verified':False,'intraperiod_liquidity_verified':False,'distribution_authorized':False,'financial_module_closed':False,'decision':'PENDING','run_ready':False,'production_authorized':False}
    encoded=canonical(p);return ProjectCashRun(encoded,digest(encoded))
