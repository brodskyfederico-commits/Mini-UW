"""T72 same-liability scheduled phase anchor, never a second funding event."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json,re
from .drafts import ValidationError,canonical,digest,nonempty
from .construction_bundle import recover_construction_bundle
from .preopening_cash import _object
from .lifecycle_bundle import _bytes,_shape,_list
from .debt_service import parse_loan_terms,produce_debt_service,DateWindow,DebtServiceRun,_fraction
from .debt_closing import DatedLoanEvidence

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T72-T75.md'


@dataclass(frozen=True)
class OperatingDebtPhaseRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def operating_loans(self):
        if self.payload['state']!='matched_synthetic_same_liability_operating_phase':return None
        return tuple(DatedLoanEvidence(loan_raw=row['schedule_source_utf8'].encode(),windows=tuple(DateWindow(**w)for w in row['windows']),run=DebtServiceRun(**row['schedule_run']))for row in self.payload['loan_phases'])


def produce_operating_debt_phase(bundle_raw,spec_raw):
    recovered=recover_construction_bundle(bundle_raw);construction=recovered.run;p=construction.payload;s=_object(spec_raw)
    keys={'schema','profile','construction_bundle_sha256','construction_cash_run_sha256','phase_basis_ref','loan_phases'}
    if type(s)is not dict or set(s)!=keys or s['schema']!='miniuw.synthetic-operating-debt-phase.v1'or s['profile']!='SYNTHETIC-SAME-LIABILITY-NO-NEW-CASH-NO-EXTENSION-v1':raise ValidationError('exact same-liability operating phase profile required')
    blockers=[];rows=[];sources={e.run.payload['loan_id']:e for e in recovered.loans};seen=set()
    for key,value in [('construction_bundle_sha256',recovered.bundle_sha256),('construction_cash_run_sha256',construction.sha256)]:
        if type(s[key])is not str or not re.fullmatch('[a-f0-9]{64}',s[key]):raise ValidationError('exact construction source/run hash required')
        if s[key]!=value:blockers.append(key+'_mismatch')
    if s['phase_basis_ref']is None:blockers.append('operating_phase_contract_basis_missing')
    else:nonempty(s['phase_basis_ref'],'phase_basis_ref')
    if p['state']!='reconciled_synthetic_staged_preopening_cash':blockers.append('construction_cash_or_draws_blocked')
    cash=construction.preopening_run;cash_payload=None if cash is None else cash.payload
    if type(s['loan_phases'])is not list or not 1<=len(s['loan_phases'])<=32:raise ValidationError('one to 32 explicit operating phase records required')
    for row in s['loan_phases']:
        keys={'loan_id','construction_loan_source_sha256','construction_loan_run_sha256','same_liability_declared','no_new_cash_declared','no_principal_adjustments_declared','prior_interest_fees_settled_declared','continuity_basis_ref','settlement_basis_ref','schedule_source_utf8','windows'}
        _shape(row,keys);loan=row['loan_id'];nonempty(loan,'loan_id')
        if loan in seen:raise ValidationError('duplicate operating phase loan identity')
        seen.add(loan);local=[];source=sources.get(loan)
        for key in ['same_liability_declared','no_new_cash_declared','no_principal_adjustments_declared','prior_interest_fees_settled_declared']:
            if row[key]is not None and type(row[key])is not bool:raise ValidationError('explicit phase declaration or unresolved null required')
            if row[key]is not True:local.append(key+'_not_explicitly_true')
        for key in ['continuity_basis_ref','settlement_basis_ref']:
            if row[key]is None:local.append(key+'_missing')
            else:nonempty(row[key],key)
        for key in ['construction_loan_source_sha256','construction_loan_run_sha256']:
            if type(row[key])is not str or not re.fullmatch('[a-f0-9]{64}',row[key]):raise ValidationError('exact staged loan source/run SHA required')
        raw=_bytes(row['schedule_source_utf8']);terms=parse_loan_terms(raw)
        windows=tuple(DateWindow(**_shape(w,['window_id','start_date','end_date','boundary']))for w in _list(row['windows'],128));schedule=produce_debt_service(raw,windows)
        if terms['loan_id']!=loan:local.append('operating_schedule_loan_identity_mismatch')
        if terms['context']!=p['context']or terms['currency']!=p['currency']:local.append('operating_phase_context_or_currency_mismatch')
        carry=None;cash_carry=None;at=None;original_maturity=None
        if source is None:local.append('construction_loan_evidence_missing')
        else:
            sp=source.run.payload;at=sp['end_date'];original_maturity=sp['maturity_date']
            if row['construction_loan_source_sha256']!=hashlib.sha256(source.raw).hexdigest()or row['construction_loan_run_sha256']!=source.run.sha256:local.append('construction_loan_binding_mismatch')
            if sp['state']!='computed_synthetic_construction_draw_plan':local.append('construction_loan_plan_blocked')
            else:
                carry=sp['totals']['terminal_principal'];value=_fraction(carry,1300)
                if value<=0:local.append('nonpositive_carry_requires_loan_discharge_profile')
                if _fraction(terms['principal'])!=value:local.append('phase_principal_differs_from_construction_carry')
            if terms['origination_date']!=at:local.append('schedule_anchor_does_not_match_construction_cutoff')
            dates=terms['payment_dates']
            if dates is None or not dates or dates[-1]!=original_maturity:local.append('operating_maturity_differs_no_extension_inferred')
            if at>=original_maturity:local.append('construction_debt_due_at_or_before_operating_phase')
            if cash_payload is not None and cash_payload['state']=='reconciled_synthetic_preopening_cash':
                if cash_payload['opening_operation_date']!=at:local.append('preopening_cash_cutoff_differs_from_phase_anchor')
                cash_carry=cash_payload['date_close_balances'][-1]['loan_principal'].get(loan)
                if cash_carry is None or carry is None or _fraction(cash_carry,1300)!=_fraction(carry,1300):local.append('preopening_cash_principal_differs_from_construction_carry')
        if schedule.payload['schedule_state']!='computed_synthetic'or not schedule.payload['schedule']or any(r['date']is None for r in schedule.payload['schedule']):local.append('complete_dated_operating_schedule_unavailable')
        rows.append(dict(loan_id=loan,phase_start_date=at,original_maturity_date=original_maturity,construction_terminal_principal=carry,preopening_terminal_principal=cash_carry,
            schedule_source_utf8=row['schedule_source_utf8'],schedule_source_sha256=hashlib.sha256(raw).hexdigest(),schedule_run=asdict(schedule),windows=row['windows'],blockers=sorted(set(local))))
        blockers.extend(loan+':'+reason for reason in local)
    if seen!=set(sources):blockers.append('operating_phase_inventory_does_not_match_all_construction_loans')
    result={'component':'T72','purpose':'synthetic_same_liability_construction_to_operating_schedule','engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),
        'construction_bundle_sha256':recovered.bundle_sha256,'construction_cash_run_sha256':construction.sha256,'phase_source_sha256':hashlib.sha256(spec_raw).hexdigest(),'context':p['context'],'currency':p['currency'],
        'loan_phases':rows,'construction_blockers':p['blockers'],'construction_cash_blockers':p['cash_blockers'],'blockers':sorted(set(blockers)),
        'state':'matched_synthetic_same_liability_operating_phase'if not blockers else'blocked','schedule_anchor_is_new_funding_date':False,'new_cash_at_phase_start_generated':False,
        'capitalization_or_principal_adjustment_generated':False,'maturity_extension_generated':False,'real_contract_or_settlement_authenticated':False,
        'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return OperatingDebtPhaseRun(encoded,digest(encoded))
