"""T73 full holding/sale sources tied to staged cash and same-liability phase proof."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json,re
from .drafts import ValidationError,canonical,digest,nonempty
from .preopening_cash import _object,link_preopening_to_operation
from .construction_bundle import recover_construction_bundle
from .operating_debt_phase import OperatingDebtPhaseRun,produce_operating_debt_phase
from .settled_hold_sale import SettledHoldSaleRun,reconcile_settled_hold_sale_cash
from .holding_cash import parse_holding_cash
from .operating_cash import parse_operating_cash

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T108.md'


@dataclass(frozen=True)
class SettledOperatingWindowRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def reconcile_settled_operating_window(bundle_raw,phase_raw,phase_run,holding_args,hold_run,cash_binding_raw,spec_raw):
    if type(phase_run)is not OperatingDebtPhaseRun or produce_operating_debt_phase(bundle_raw,phase_raw)!=phase_run:raise ValidationError('entire staged-to-operating phase proof must reproduce')
    if type(holding_args)is not tuple or len(holding_args)!=6 or type(hold_run)is not SettledHoldSaleRun or reconcile_settled_hold_sale_cash(*holding_args)!=hold_run:raise ValidationError('entire holding/debt/sale proof must reproduce')
    recovered=recover_construction_bundle(bundle_raw);construction=recovered.run;p=construction.payload;h=hold_run.payload;s=_object(spec_raw)
    keys={'schema','construction_bundle_sha256','phase_run_sha256','holding_manifest_sha256','hold_sale_spec_sha256','hold_sale_run_sha256','cash_binding_sha256','same_cash_and_liability_basis_ref'}
    if type(s)is not dict or set(s)!=keys or s['schema']!='miniuw.synthetic-settled-operating-window.v1':raise ValidationError('exact staged-to-operating cash window binding required')
    actual={'construction_bundle_sha256':recovered.bundle_sha256,'phase_run_sha256':phase_run.sha256,'holding_manifest_sha256':hashlib.sha256(holding_args[2]).hexdigest(),'hold_sale_spec_sha256':hashlib.sha256(holding_args[4]).hexdigest(),'hold_sale_run_sha256':hold_run.sha256,'cash_binding_sha256':hashlib.sha256(cash_binding_raw).hexdigest()}
    blockers=[];link=None;loan_checks=[]
    for key,value in actual.items():
        if type(s[key])is not str or not re.fullmatch('[a-f0-9]{64}',s[key]):raise ValidationError('exact window source/run hash required')
        if s[key]!=value:blockers.append(key+'_mismatch')
    if s['same_cash_and_liability_basis_ref']is None:blockers.append('same_cash_and_liability_basis_missing')
    else:nonempty(s['same_cash_and_liability_basis_ref'],'same_cash_and_liability_basis_ref')
    if p['state']!='reconciled_synthetic_staged_preopening_cash':blockers.append('construction_cash_blocked')
    if phase_run.payload['state']!='matched_synthetic_same_liability_operating_phase':blockers.append('operating_debt_phase_blocked')
    if h['state']!='reconciled_synthetic_settled_hold_sale_cash':blockers.append('operating_holding_or_sale_blocked')
    if h['context']!=p['context']or h['currency']!=p['currency']:blockers.append('construction_and_operating_context_or_currency_mismatch')
    periods,sale,holding_raw,_,_,_=holding_args;m=parse_holding_cash(holding_raw);first_id=m['periods'][0]['period_ref'];first=next((e for e in periods if parse_operating_cash(e.spec_raw)['period_ref']==first_id),None)
    if first is None:blockers.append('first_operating_period_missing')
    elif construction.compiled_raw is not None and construction.preopening_run is not None:
        link=link_preopening_to_operation(construction.compiled_raw,construction.preopening_run,first,cash_binding_raw)
        if link.payload['state']!='matched_synthetic_cash_only':blockers.append('construction_operating_cash_boundary_blocked')
    else:blockers.append('compiled_construction_cash_unavailable')
    phase_loans=phase_run.operating_loans
    if phase_loans is not None:
        expected={e.run.payload['loan_id']:e for e in phase_loans};supplied={e.run.payload['loan_id']:e for e in sale.loans}
        if set(expected)!=set(supplied):blockers.append('phase_and_operating_loan_inventories_differ')
        for loan,e in expected.items():
            actual_loan=supplied.get(loan);equal=actual_loan==e
            loan_checks.append(dict(loan_id=loan,phase_schedule_source_sha256=hashlib.sha256(e.loan_raw).hexdigest(),phase_schedule_run_sha256=e.run.sha256,operating_source_windows_and_run_match=equal))
            if not equal:blockers.append(loan+':operating_schedule_source_windows_or_run_differs_from_phase')
        starts={row['phase_start_date']for row in phase_run.payload['loan_phases']}
        if starts!={h['opening_date']}:blockers.append('operating_window_does_not_start_at_all_phase_boundaries')
    result={'component':'T108-window','purpose':'synthetic_staged_debt_cash_through_operating_sale_window','engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),
        'spec_source_sha256':hashlib.sha256(spec_raw).hexdigest(),'source_bindings':actual,'context':p['context'],'currency':p['currency'],'cash_boundary_run':None if link is None else asdict(link),'loan_phase_checks':loan_checks,
        'construction_blockers':p['blockers'],'construction_cash_blockers':p['cash_blockers'],'phase_blockers':phase_run.payload['blockers'],'holding_blockers':h['blockers'],'sale_debt_blockers':h['sale_debt_blockers'],
        'blockers':sorted(set(blockers)),'state':'matched_synthetic_settled_operating_window'if not blockers else'blocked',
        'new_cash_draw_or_equity_at_phase_boundary_generated':False,'maturity_extension_generated':False,'real_contract_funding_or_payments_authenticated':False,
        'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return SettledOperatingWindowRun(encoded,digest(encoded))
