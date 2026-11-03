"""T49 bounded cost total directly into T42; no false global-affine translation."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json,re
from .drafts import ValidationError,canonical,digest
from .intake import _unique_object,_invalid_constant
from .debt_service import _fraction
from .exit_value import ExitValueRun,produce_exit_value
from .bounded_sale_costs import BoundedSaleCostsRun,produce_bounded_sale_costs
from .costed_exit_sale import parse_costed_exit_sale
from .exit_sale_bridge import assemble_exit_sale,ExitSaleBridgeRun
from .project_sale_revision import verify_evidence,evidence_fingerprint

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION_PATH=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T48-T50.md'


def parse_bounded_exit_sale(raw):
    if type(raw)is not bytes or not raw or len(raw)>131072:raise ValidationError('bounded explicit bounded-exit specification required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid bounded-exit JSON')from error
    keys={'schema','revision_id','base_evidence_sha256','exit_spec_sha256','exit_run_sha256','sale_node_id',
        'sale_at_value_hypothesis_ref','unchanged_other_sources_basis_ref','equity_funding_assumption_ref',
        'cost_source_sha256','cost_run_sha256','bounds_source_sha256','bounded_run_sha256'}
    if type(p)is not dict or set(p)!=keys or p['schema']!='miniuw.synthetic-bounded-exit-sale.v1':raise ValidationError('exact bounded-exit source bindings required')
    base={k:v for k,v in p.items()if k not in ['bounds_source_sha256','bounded_run_sha256']};base['schema']='miniuw.synthetic-costed-exit-sale.v1'
    parse_costed_exit_sale(canonical(base).encode())
    for key in ['bounds_source_sha256','bounded_run_sha256']:
        if type(p[key])is not str or not re.fullmatch('[a-f0-9]{64}',p[key]):raise ValidationError('exact bound source/run SHA required')
    return p


@dataclass(frozen=True)
class BoundedExitSaleRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def exit_sale_run(self):
        p=self.payload['exit_sale_run'];return None if p is None else ExitSaleBridgeRun(**p)


def assemble_bounded_exit_sale(evidence,noi_raw,noi_run,exit_spec_raw,exit_run,cost_raw,cost_run,bounds_raw,bounded_run,spec_raw):
    spec=parse_bounded_exit_sale(spec_raw);verify_evidence(evidence)
    if type(exit_run)is not ExitValueRun or produce_exit_value(noi_raw,noi_run,exit_spec_raw)!=exit_run:raise ValidationError('exit value must reproduce')
    if type(bounded_run)is not BoundedSaleCostsRun or produce_bounded_sale_costs(cost_raw,cost_run,bounds_raw)!=bounded_run:raise ValidationError('complete original costs and limit rules must reproduce')
    p=exit_run.payload;c=bounded_run.payload;blockers=[];br=None;run=None
    actual={'base_evidence_sha256':evidence_fingerprint(evidence),'exit_spec_sha256':hashlib.sha256(exit_spec_raw).hexdigest(),'exit_run_sha256':exit_run.sha256,
        'cost_source_sha256':hashlib.sha256(cost_raw).hexdigest(),'cost_run_sha256':cost_run.sha256,'bounds_source_sha256':hashlib.sha256(bounds_raw).hexdigest(),'bounded_run_sha256':bounded_run.sha256}
    for key,value in actual.items():
        if spec[key]!=value:blockers.append(key+'_mismatch')
    if p['state']!='computed_synthetic_exit_value':blockers.append('computed_exit_value_unavailable')
    if c['state']!='computed_synthetic_bounded_costs':blockers.append('computed_complete_bounded_costs_unavailable')
    if c['context']!=p['context']or c['currency']!=p['currency']or c['sale_date']!=p['valuation_date']:blockers.append('bounded_cost_and_exit_context_currency_or_date_mismatch')
    expected_ref='miniuw:synthetic-exit-value:'+exit_run.sha256+'#/candidate_value'
    if _fraction(c['gross_price']['value'],max_digits=1300)!=_fraction(p['candidate_value'],max_digits=1300)or c['gross_price']['source_ref']!=expected_ref:blockers.append('bounded_cost_price_or_exit_run_lineage_mismatch')
    if not blockers:
        bridge={k:v for k,v in spec.items()if k not in ['cost_source_sha256','cost_run_sha256','bounds_source_sha256','bounded_run_sha256']}
        bridge.update(schema='miniuw.synthetic-exit-value-to-sale.v1',closing_cost_claim=dict(value=c['total_closing_cost'],currency=c['currency'],as_of_date=c['sale_date'],basis='cash_flow_at_closing',source_ref='miniuw:synthetic-bounded-sale-costs:'+bounded_run.sha256+'#/total_closing_cost'))
        br=canonical(bridge).encode();run=assemble_exit_sale(evidence,noi_raw,noi_run,exit_spec_raw,exit_run,br);blockers.extend(run.payload['blockers'])
    result={'component':'T49','purpose':'synthetic_bounded_costs_to_guarded_exit_sale',
        'engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION_PATH.read_bytes()).hexdigest(),
        'spec_sha256':hashlib.sha256(spec_raw).hexdigest(),'input_bindings':actual,'computed_closing_cost':c['total_closing_cost'],
        'generated_exit_sale_spec_json':None if br is None else br.decode(),'exit_sale_run':None if run is None else asdict(run),
        'state':'compiled_synthetic'if run is not None and run.payload['state']=='compiled_synthetic'and not blockers else'blocked',
        'blockers':sorted(set(blockers)),'bounded_cost_blockers':c['blockers'],'original_cost_blockers':c['original_cost_blockers'],
        'global_affine_recovery_analysis_produced':False,'evidence_currency_checked':False,'contract_or_tax_rule_verified':False,
        'bank_credit_approved':False,'personal_investor_return':None,'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return BoundedExitSaleRun(encoded,digest(encoded))


def verify_bounded_exit_sale(evidence,noi_raw,noi_run,exit_spec_raw,exit_run,cost_raw,cost_run,bounds_raw,bounded_run,spec_raw,report):
    if type(report)is not BoundedExitSaleRun or digest(report.payload_json)!=report.sha256:raise ValidationError('typed bounded-exit result with matching hash required')
    if assemble_bounded_exit_sale(evidence,noi_raw,noi_run,exit_spec_raw,exit_run,cost_raw,cost_run,bounds_raw,bounded_run,spec_raw)!=report:raise ValidationError('bounded-exit report replay mismatch')
    return report
