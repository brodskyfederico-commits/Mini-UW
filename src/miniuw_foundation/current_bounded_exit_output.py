"""T50 explicit-time full-source gate for the distinct bounded-cost sale profile."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,json
from .drafts import ValidationError,canonical,digest
from .bounded_exit_sale import BoundedExitSaleRun,assemble_bounded_exit_sale
from .current_exit_output import required_exit_sources
from .evidence_currency import EvidenceCurrencyRun,evaluate_evidence_currency

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION_PATH=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T48-T50.md'


def required_bounded_exit_sources(arguments):
    if type(arguments)is not tuple or len(arguments)!=10:raise ValidationError('complete immutable bounded-exit arguments required')
    # The shared byte-inventory helper does not execute a financial profile.
    rows=required_exit_sources((*arguments[:7],arguments[9]))
    rows.append(dict(requirement_id='/exit/cost_bounds',source_sha256=hashlib.sha256(arguments[7]).hexdigest(),source_locator='/exit/cost_bounds'))
    return rows


@dataclass(frozen=True)
class CurrentBoundedExitOutputRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def assemble_current_bounded_exit_output(arguments,base_run,registry_raw,registry_run,as_of):
    if type(arguments)is not tuple or len(arguments)!=10 or type(base_run)is not BoundedExitSaleRun:raise ValidationError('typed complete bounded-exit source/run required')
    if assemble_bounded_exit_sale(*arguments)!=base_run:raise ValidationError('entire bounded exit must reproduce')
    if type(registry_run)is not EvidenceCurrencyRun or evaluate_evidence_currency(registry_raw,as_of)!=registry_run:raise ValidationError('entire registry must reproduce at exact evaluation time')
    required=required_bounded_exit_sources(arguments);p=base_run.payload;r=registry_run.payload;blockers=[];output=None
    supplied=[row['requirement']for row in r['requirements']]
    if sorted(required,key=lambda x:x['requirement_id'])!=sorted(supplied,key=lambda x:x['requirement_id']):blockers.append('complete_bounded_exit_source_inventory_mismatch')
    if r['context']!=arguments[4].payload['context']:blockers.append('registry_and_bounded_exit_context_mismatch')
    if r['state']!='current_synthetic_evidence':blockers.append('required_evidence_not_current')
    if p['state']!='compiled_synthetic':blockers.append('guarded_bounded_calculation_blocked')
    if not blockers:
        investor=base_run.exit_sale_run.sale_revision_run.guarded_run.investor_run.payload
        output={key:investor[key]for key in ['equity_level','currency','gross_contributions','gross_distributions','net_cash_profit','equity_multiple',
            'cash_horizon','cash_by_category','normalized_story','capital_snapshots','annual_cash_receipts','periodic_irr','annual_irr_roots','selected_IRR']}
        output.update(dated_events=investor['events'],upstream_story_blockers=investor['story_blockers'],
            bounded_sale_cost_rows=arguments[8].payload['adjusted_costs'],total_bounded_closing_cost=arguments[8].payload['total_closing_cost'],
            personal_investor_return=None,decision='PENDING')
        risk=base_run.exit_sale_run.sale_revision_run.payload['risk_run']
        output['risk_observations']=None if risk is None else json.loads(risk['payload_json'])['metrics']
    result={'component':'T50','purpose':'synthetic_current_evidence_bounded_exit_output_gate',
        'engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION_PATH.read_bytes()).hexdigest(),
        'base_bounded_exit_run_sha256':base_run.sha256,'registry_source_sha256':hashlib.sha256(registry_raw).hexdigest(),'registry_run_sha256':registry_run.sha256,
        'evaluated_as_of_UTC':as_of,'context':arguments[4].payload['context'],'currency':arguments[4].payload['currency'],'required_source_bindings':required,
        'state':'current_synthetic_bounded_output_at_declared_time'if output is not None else'PENDING','current_project_return_summary':output,
        'blockers':sorted(set(blockers)),'calculation_blockers':p['blockers'],'evidence_blockers':r['blockers'],
        'bounded_cost_blockers':p['bounded_cost_blockers'],'original_cost_blockers':p['original_cost_blockers'],
        'historical_calculation_preserved':True,'professional_review_authenticated':False,'contract_or_tax_rule_verified':False,
        'global_affine_recovery_analysis_produced':False,'live_expiry_monitor_enabled':False,'financial_publication_authorized':False,
        'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return CurrentBoundedExitOutputRun(encoded,digest(encoded))


def verify_current_bounded_exit_output(arguments,base_run,registry_raw,registry_run,as_of,report):
    if type(report)is not CurrentBoundedExitOutputRun or digest(report.payload_json)!=report.sha256:raise ValidationError('typed current bounded-output report with matching hash required')
    if assemble_current_bounded_exit_output(arguments,base_run,registry_raw,registry_run,as_of)!=report:raise ValidationError('current bounded-output report replay mismatch')
    return report
