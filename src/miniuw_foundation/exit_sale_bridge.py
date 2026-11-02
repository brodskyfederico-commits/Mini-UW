"""T42 explicit hypothetical sale at conditional value through T39/T36 guards."""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib
import json
import re

from .drafts import ValidationError,canonical,digest,nonempty
from .intake import _unique_object,_invalid_constant
from .debt_service import _fraction
from .investor_returns import _date
from .exit_value import ExitValueRun,produce_exit_value
from .project_sale_revision import (verify_evidence,evidence_fingerprint,revise_project_sale,
                                   ProjectSaleRevisionRun)

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION_PATH=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T41-T42.md'


def parse_exit_sale_bridge(raw):
    if type(raw) is not bytes or not raw or len(raw)>131072:raise ValidationError('bounded explicit exit-sale bridge required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except (UnicodeError,ValueError,RecursionError) as error:raise ValidationError('invalid exit-sale bridge JSON')from error
    keys={'schema','revision_id','base_evidence_sha256','exit_spec_sha256','exit_run_sha256','sale_node_id',
          'sale_at_value_hypothesis_ref','unchanged_other_sources_basis_ref','equity_funding_assumption_ref','closing_cost_claim'}
    if type(p) is not dict or set(p)!=keys or p['schema']!='miniuw.synthetic-exit-value-to-sale.v1':
        raise ValidationError('exact explicit hypothetical-value-to-sale profile required')
    for key in ['revision_id','sale_node_id']:nonempty(p[key],key)
    for key in ['base_evidence_sha256','exit_spec_sha256','exit_run_sha256']:
        if type(p[key]) is not str or not re.fullmatch('[a-f0-9]{64}',p[key]):raise ValidationError('exact source/run binding required')
    for key in ['sale_at_value_hypothesis_ref','unchanged_other_sources_basis_ref','equity_funding_assumption_ref']:
        if p[key] is not None:nonempty(p[key],key)
    claim=p['closing_cost_claim']
    if type(claim) is not dict or set(claim)!={'value','currency','as_of_date','basis','source_ref'}:
        raise ValidationError('explicit full closing-cost claim required')
    _fraction(claim['value'])
    for key in ['currency','basis','source_ref']:
        if claim[key] is not None:nonempty(claim[key],key)
    if claim['as_of_date'] is not None:_date(claim['as_of_date'])
    return p


@dataclass(frozen=True)
class ExitSaleBridgeRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)
    @property
    def sale_revision_run(self):
        p=self.payload['sale_revision_run'];return None if p is None else ProjectSaleRevisionRun(**p)


def assemble_exit_sale(evidence,noi_raw,noi_run,exit_spec_raw,exit_run,bridge_raw):
    spec=parse_exit_sale_bridge(bridge_raw)
    verify_evidence(evidence)
    if type(exit_run) is not ExitValueRun or produce_exit_value(noi_raw,noi_run,exit_spec_raw)!=exit_run:
        raise ValidationError('entire forward NOI/value source/run must reproduce')
    p=exit_run.payload;blockers=[];revision_raw=None;revision=None;existing_valuation=None
    for key,actual in [('base_evidence_sha256',evidence_fingerprint(evidence)),
                       ('exit_spec_sha256',hashlib.sha256(exit_spec_raw).hexdigest()),('exit_run_sha256',exit_run.sha256)]:
        if spec[key]!=actual:blockers.append(key+'_mismatch')
    if p['state']!='computed_synthetic_exit_value':blockers.append('computed_exit_value_unavailable')
    if spec['sale_at_value_hypothesis_ref'] is None:blockers.append('explicit_hypothetical_sale_at_value_basis_missing')
    if spec['unchanged_other_sources_basis_ref'] is None:blockers.append('explicit_other_sources_hypothesis_missing')
    sale=next((c for c in evidence.closings if c.closing_id==spec['sale_node_id']),None)
    if sale is None:blockers.append('exact_sale_node_not_identified')
    else:
        source=json.loads(sale.closing_raw)
        if source['kind']!='sale':blockers.append('target_is_not_sale')
        if source['closing_date']!=p['valuation_date']:blockers.append('valuation_date_not_sale_date')
        if source['context']!=p['context'] or source['currency']!=p['currency']:blockers.append('sale_and_value_context_or_currency_mismatch')
        existing_valuation=source['valuation_claim']
        if existing_valuation is not None:
            declared=_fraction(existing_valuation['value'])
            candidate=None if p['candidate_value'] is None else _fraction(p['candidate_value'],max_digits=1300)
            if (declared is None or declared<0 or existing_valuation['currency']!=p['currency']
                    or existing_valuation['as_of_date']!=p['valuation_date']
                    or existing_valuation['basis']!='valuation_not_cash' or existing_valuation['source_ref'] is None):
                blockers.append('existing_sale_valuation_claim_unresolved_or_incompatible')
            elif candidate is not None and declared!=candidate:
                blockers.append('existing_sale_valuation_claim_conflicts_with_computed_value')
    if not blockers:
        claim={'value':p['candidate_value'],'currency':p['currency'],'as_of_date':p['valuation_date'],
               'basis':'cash_flow_at_closing','source_ref':'miniuw:synthetic-exit-value:'+exit_run.sha256+
               '#/candidate_value;hypothesis:'+spec['sale_at_value_hypothesis_ref']}
        revised={'schema':'miniuw.synthetic-project-sale-source-revision.v1','revision_id':spec['revision_id'],
            'base_evidence_sha256':spec['base_evidence_sha256'],'sale_node_id':spec['sale_node_id'],
            'unchanged_other_sources_basis_ref':spec['unchanged_other_sources_basis_ref'],
            'equity_funding_assumption_ref':spec['equity_funding_assumption_ref'],
            'replacement_claims':{'gross_proceeds':claim,'closing_costs_paid':spec['closing_cost_claim']}}
        revision_raw=canonical(revised).encode();revision=revise_project_sale(evidence,revision_raw)
        blockers.extend(revision.payload['blockers'])
    result={'component':'T42','purpose':'synthetic_hypothetical_exit_value_to_guarded_sale',
        'engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION_PATH.read_bytes()).hexdigest(),
        'bridge_spec_sha256':hashlib.sha256(bridge_raw).hexdigest(),'exit_spec_sha256':hashlib.sha256(exit_spec_raw).hexdigest(),
        'exit_run_sha256':exit_run.sha256,'base_evidence_sha256':evidence_fingerprint(evidence),
        'candidate_value':p['candidate_value'],'sale_at_value_hypothesis_ref':spec['sale_at_value_hypothesis_ref'],
        'existing_sale_valuation_claim':existing_valuation,
        'sale_revision_spec_json':None if revision_raw is None else revision_raw.decode(),
        'sale_revision_run':None if revision is None else asdict(revision),
        'state':'compiled_synthetic' if revision is not None and revision.payload['state']=='compiled_synthetic' and not blockers else 'blocked',
        'blockers':sorted(set(blockers)),'exit_value_blockers':p['blockers'],
        'value_also_added_as_separate_investor_receipt':False,'actual_sale_price_or_cash_verified':False,
        'costs_recomputed_from_price':False,'bank_credit_approved':False,'personal_investor_return':None,
        'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return ExitSaleBridgeRun(encoded,digest(encoded))


def verify_exit_sale(evidence,noi_raw,noi_run,exit_spec_raw,exit_run,bridge_raw,report):
    if type(report) is not ExitSaleBridgeRun or digest(report.payload_json)!=report.sha256:
        raise ValidationError('typed exit-sale report with matching hash required')
    if assemble_exit_sale(evidence,noi_raw,noi_run,exit_spec_raw,exit_run,bridge_raw)!=report:
        raise ValidationError('exit-sale report replay mismatch')
    return report
