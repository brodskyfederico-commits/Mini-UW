"""T31 exact scheduled-date debt/closing comparison under explicit payment assumptions."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import hashlib,json,re
from .drafts import ContextSeed,ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant
from .debt_service import DateWindow,DebtServiceRun,parse_loan_terms,produce_debt_service,_fraction,rational
from .closing_cash import ClosingCashRun,parse_closing_cash,produce_closing_cash
from .operating_noi import _bounded,ArithmeticBudgetError

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SCHEMA='miniuw.synthetic-debt-closing.v1'
MODES={'before_regular_payment','after_regular_payment_before_balloon','at_origination_no_accrual'}


@dataclass(frozen=True,kw_only=True)
class DatedLoanEvidence:
    loan_raw:bytes
    windows:tuple[DateWindow,...]
    run:DebtServiceRun
    def __post_init__(self):
        if type(self.loan_raw)is not bytes or type(self.run)is not DebtServiceRun or type(self.windows)is not tuple or len(self.windows)>128 or any(type(w)is not DateWindow for w in self.windows):raise ValidationError('immutable typed dated loan evidence required')


def parse_debt_closing(raw):
    if type(raw)is not bytes or not raw or len(raw)>1_048_576:raise ValidationError('bounded explicit debt/closing specification required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid debt/closing JSON')from error
    if type(p)is not dict or set(p)!={'schema','profile','context','currency','closing_source_sha256','closing_run_sha256','loans'}or p['schema']!=SCHEMA or p['profile']!='SYNTHETIC-EXACT-SCHEDULED-CUTOFF-FULL-PAYOFF-v1':raise ValidationError('exact scheduled-cutoff-only full-payoff profile required')
    if type(p['context'])is not dict:raise ValidationError('explicit synthetic context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact context required')from error
    nonempty(p['currency'],'currency')
    for key in ['closing_source_sha256','closing_run_sha256']:
        if type(p[key])is not str or not re.fullmatch('[a-f0-9]{64}',p[key]):raise ValidationError('exact closing source/run SHA-256 required')
    if type(p['loans'])is not list or len(p['loans'])>64:raise ValidationError('bounded explicit old-loan binding inventory required')
    seen=set()
    for row in p['loans']:
        keys={'loan_id','loan_source_sha256','loan_run_sha256','payment_cutoff','prior_regular_service_assumed_paid','unmodeled_debt_changes_declared_absent','payment_assumption_basis_ref','cutoff_basis_ref','fees_and_other_scope_basis_ref'}
        if type(row)is not dict or set(row)!=keys:raise ValidationError('exact loan cutoff and assumption fields required')
        nonempty(row['loan_id'],'loan_id')
        if row['loan_id']in seen:raise ValidationError('duplicate old-loan binding')
        seen.add(row['loan_id'])
        for key in ['loan_source_sha256','loan_run_sha256']:
            if type(row[key])is not str or not re.fullmatch('[a-f0-9]{64}',row[key]):raise ValidationError('exact loan source/run SHA-256 required')
        if row['payment_cutoff']not in MODES:raise ValidationError('unsupported cutoff: no stub accrual or automatic maturity extension')
        for key in ['prior_regular_service_assumed_paid','unmodeled_debt_changes_declared_absent']:
            if row[key]is not None and type(row[key])is not bool:raise ValidationError('explicit assumption declaration or null required')
        for key in ['payment_assumption_basis_ref','cutoff_basis_ref','fees_and_other_scope_basis_ref']:
            if row[key]is not None:nonempty(row[key],key)
    return p


def verify_loans(loans):
    if type(loans)is not tuple or len(loans)>64 or any(type(e)is not DatedLoanEvidence for e in loans):raise ValidationError('bounded immutable dated loan inventory required')
    if sum(len(e.loan_raw)for e in loans)>8_388_608:raise ValidationError('loan source transport budget exceeded')
    sources={}
    for e in loans:
        terms=parse_loan_terms(e.loan_raw)
        if terms['loan_id']in sources:raise ValidationError('duplicate supplied loan identity')
        if produce_debt_service(e.loan_raw,e.windows)!=e.run:raise ValidationError('every supplied loan source/window/run must reproduce')
        sources[terms['loan_id']]=(e,terms)
    return sources


def definition_sources():
    root=Path(__file__).resolve().parents[2];refs=[]
    for path,marker in [('docs/model-refinance-contract.md','## Contrato de pago amortizante'),('docs/model-refinance-contract.md','| M6-08 |'),('docs/operating-settlement-bridges.md','## Deuda, valorización y representación')]:
        raw=(root/path).read_bytes();hits=[i+1 for i,line in enumerate(raw.decode().splitlines())if line.startswith(marker)]
        if len(hits)!=1:raise ValidationError('debt-closing definition locator changed')
        refs.append({'path':path,'line':hits[0],'sha256':hashlib.sha256(raw).hexdigest()})
    return refs


@dataclass(frozen=True)
class DebtClosingRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def reconcile_debt_closing(loans,closing_raw,closing_run,spec_raw):
    if type(closing_run)is not ClosingCashRun or produce_closing_cash(closing_raw)!=closing_run:raise ValidationError('closing source/run must reproduce')
    s=parse_debt_closing(spec_raw);sources=verify_loans(loans);closing=parse_closing_cash(closing_raw);c=closing_run.payload;blockers=[];rows=[]
    for key,actual in [('closing_source_sha256',c['source_sha256']),('closing_run_sha256',closing_run.sha256)]:
        if s[key]!=actual:blockers.append(key+'_mismatch')
    if s['context']!=c['context']:blockers.append('closing_context_mismatch')
    if s['currency']!=c['currency']:blockers.append('closing_currency_mismatch')
    if c['state']!='computed_synthetic_closing':blockers.append('closing_plan_blocked')
    expected={d['loan_id']for d in closing['old_debts']};bindings={b['loan_id']:b for b in s['loans']}
    if set(bindings)!=expected:blockers.append('cutoff_binding_inventory_does_not_match_all_old_debts')
    if set(sources)!=expected:blockers.append('loan_evidence_inventory_does_not_match_all_old_debts')
    for index,debt in enumerate(closing['old_debts']):
        key=debt['loan_id'];binding=bindings.get(key);found=sources.get(key);local=[];principal=interest=None;payment_index=None;assumed_indices=[];schedule_pointer=None;balloon=None;residuals={}
        if binding is None:local.append('loan_cutoff_binding_missing')
        if found is None:local.append('loan_evidence_missing')
        if binding is not None and found is not None:
            evidence,terms=found;d=evidence.run.payload
            for field,actual in [('loan_source_sha256',hashlib.sha256(evidence.loan_raw).hexdigest()),('loan_run_sha256',evidence.run.sha256)]:
                if binding[field]!=actual:local.append(field+'_mismatch')
            if d['context']!=c['context']:local.append('loan_closing_context_mismatch')
            if d['currency']!=c['currency']:local.append('loan_closing_currency_mismatch')
            if binding['prior_regular_service_assumed_paid']is not True:local.append('prior_regular_service_payment_assumption_missing_or_false')
            if binding['unmodeled_debt_changes_declared_absent']is not True:local.append('unmodeled_debt_changes_not_declared_absent')
            for field in ['payment_assumption_basis_ref','cutoff_basis_ref','fees_and_other_scope_basis_ref']:
                if binding[field]is None:local.append(field+'_missing')
            dated=d['schedule_state']=='computed_synthetic'and d['schedule']and all(r['date']is not None for r in d['schedule'])
            if not dated:local.append('complete_dated_computed_schedule_unavailable')
            if dated:
                mode=binding['payment_cutoff'];date=c['closing_date'];selected=next((r for r in d['schedule']if r['date']==date),None)
                if mode=='at_origination_no_accrual':
                    if date!=terms['origination_date']:local.append('closing_not_at_explicit_origination_date')
                    else:principal=_fraction(terms['principal']);interest=Fraction(0);schedule_pointer='/principal_at_origination'
                elif selected is None:local.append('cutoff_not_an_exact_scheduled_payment_date_no_stub_or_extension_inferred')
                else:
                    payment_index=selected['payment_index'];before=mode=='before_regular_payment';last_assumed=payment_index-1 if before else payment_index
                    assumed_indices=list(range(1,last_assumed+1));principal=_fraction(selected['opening_balance'if before else'closing_balance'],1300)
                    interest=_fraction(selected['interest_due'],1300)if before else Fraction(0)
                    balloon=_fraction(selected['balloon_due'],1300)
                    schedule_pointer='/schedule/'+str(payment_index-1)+'/'+('opening_balance'if before else'closing_balance')
                if principal is not None:
                    try:
                        for category,expected_value in [('principal',principal),('interest',interest)]:
                            claim=_fraction(debt[category+'_due']['value'])
                            residuals[category]=None if claim is None else rational(_bounded(claim-expected_value))
                            if claim is None:local.append(category+'_closing_claim_missing')
                            elif claim!=expected_value:local.append(category+'_closing_claim_differs_from_computed_schedule_cutoff')
                    except ArithmeticBudgetError:local.append('debt_closing_exact_arithmetic_budget_exceeded');principal=interest=None;residuals={}
        rows.append({'loan_id':key,'closing_old_debt_pointer':'/old_debts/'+str(index),'closing_date':c['closing_date'],
            'binding':binding,'loan_run_sha256':None if found is None else found[0].run.sha256,
            'loan_payment_blockers':[]if found is None else found[0].run.payload['payment_blockers'],
            'loan_schedule_blockers':[]if found is None else found[0].run.payload['schedule_blockers'],
            'selected_payment_index':payment_index,'assumed_paid_regular_payment_indices':assumed_indices,
            'principal_schedule_pointer':schedule_pointer,'computed_principal_to_close':None if principal is None else rational(principal),
            'computed_regular_interval_interest_to_close':None if interest is None else rational(interest),
            'scheduled_row_balloon_due':None if balloon is None else rational(balloon),'balloon_added_again_to_principal':False,
            'declared_principal_due':debt['principal_due'],'declared_interest_due':debt['interest_due'],
            'claim_minus_expected_residuals':residuals,'blockers':local,
            'fees_and_other_obligations_source':'supplied_closing_claims_not_schedule_generated',
            'scheduled_payment_history_actually_verified':False})
        blockers.extend(key+':'+reason for reason in local)
    p={'component':'T31','purpose':'synthetic_dated_debt_to_closing_comparison','engine_sha256':ENGINE_SHA256,
        'spec_source_sha256':hashlib.sha256(spec_raw).hexdigest(),'closing_source_sha256':c['source_sha256'],'closing_run_sha256':closing_run.sha256,
        'definition_sources':definition_sources(),'context':c['context'],'currency':c['currency'],'closing_date':c['closing_date'],
        'loans':rows,'all_supplied_loans_replayed':True,'blockers':sorted(set(blockers)),'closing_blockers':c['blockers'],
        'state':'matched_synthetic_debt_assumptions'if not blockers else'blocked',
        'closing_source_changed':False,'payment_assumptions_adopted':False,'scheduled_payment_history_actually_verified':False,
        'bank_payoff_statement_verified':False,'actual_debt_discharge_verified':False,'whole_project_cash_reconciled':False,
        'distribution_authorized':False,'financial_module_closed':False,'decision':'PENDING','run_ready':False,'production_authorized':False}
    encoded=canonical(p);return DebtClosingRun(encoded,digest(encoded))
