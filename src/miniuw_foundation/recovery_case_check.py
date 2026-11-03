"""T53 compare a separately supplied full sale replay against its recovery curve."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,json
from .drafts import ValidationError,canonical,digest
from .debt_service import _fraction,rational
from .operating_noi import _bounded,ArithmeticBudgetError
from .bounded_exit_sale import BoundedExitSaleRun,assemble_bounded_exit_sale
from .bounded_sale_recovery import BoundedSaleRecoveryRun,analyze_bounded_sale_recovery

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION_PATH=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T53.md'


def _without(record,paths):
    p=json.loads(canonical(record))
    for path in paths:
        target=p
        for key in path[:-1]:target=target[key]
        target.pop(path[-1],None)
    return p


@dataclass(frozen=True)
class RecoveryCaseCheckRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def check_recovery_case(reference_arguments,reference_run,recovery_spec_raw,recovery_run,candidate_arguments,candidate_run):
    if type(recovery_run)is not BoundedSaleRecoveryRun or analyze_bounded_sale_recovery(reference_arguments,reference_run,recovery_spec_raw)!=recovery_run:
        raise ValidationError('complete reference and recovery analysis must reproduce')
    if type(candidate_arguments)is not tuple or len(candidate_arguments)!=10 or type(candidate_run)is not BoundedExitSaleRun or assemble_bounded_exit_sale(*candidate_arguments)!=candidate_run:
        raise ValidationError('complete candidate source/run must reproduce')
    r=reference_arguments;c=candidate_arguments;p=recovery_run.payload;blockers=[];comparison=None
    if p['state']!='computed_synthetic_piecewise_recovery':blockers.append('reference_recovery_unavailable')
    if candidate_run.payload['state']!='compiled_synthetic':blockers.append('candidate_guarded_return_blocked')
    if r[0]!=c[0]:blockers.append('project_debt_operation_funding_or_investor_inputs_changed')
    if r[1:3]!=c[1:3]:blockers.append('forward_noi_source_or_run_changed')
    allowed=[(3,[('cap_rate','value'),('cap_rate','source_ref')]),
             (5,[('gross_price','value'),('gross_price','source_ref')]),
             (7,[('cost_source_sha256',),('cost_run_sha256',)]),
             (9,[(key,)for key in ['exit_spec_sha256','exit_run_sha256','cost_source_sha256','cost_run_sha256','bounds_source_sha256','bounded_run_sha256','revision_id']])]
    for index,paths in allowed:
        if _without(json.loads(r[index]),paths)!=_without(json.loads(c[index]),paths):blockers.append('fixed_profile_source_changed_at_argument_'+str(index))
    price=None if c[4].payload['candidate_value']is None else _fraction(c[4].payload['candidate_value'],max_digits=1300)
    lower=_fraction(p['gross_price_domain']['lower']);upper=_fraction(p['gross_price_domain']['upper'])
    if price is None or lower is None or upper is None or not lower<=price<=upper:blockers.append('candidate_price_outside_declared_domain')
    if not blockers:
        try:
            predictions=[]
            for segment in p['analysis']['segments']:
                interval=segment['price_interval']
                if _fraction(interval['lower'],max_digits=1300)<=price<=_fraction(interval['upper'],max_digits=1300):
                    def at(a,b):return _bounded(_bounded(_fraction(segment[a],max_digits=1300)*price)+_fraction(segment[b],max_digits=1300))
                    predictions.append((at('cost_slope','cost_intercept'),at('cash_profit_slope','cash_profit_intercept')))
            if not predictions:raise ValidationError('complete curve did not cover candidate price')
            if len(set(predictions))!=1:raise ValidationError('curve endpoints disagree')
            predicted_cost,predicted_profit=predictions[0]
            actual_cost=_fraction(candidate_run.payload['computed_closing_cost'],max_digits=1300)
            investor=candidate_run.exit_sale_run.sale_revision_run.guarded_run.investor_run.payload
            actual_profit=_fraction(investor['net_cash_profit'],max_digits=1300)
            if predicted_cost!=actual_cost:blockers.append('curve_cost_does_not_match_full_replay')
            if predicted_profit!=actual_profit:blockers.append('curve_profit_does_not_match_full_replay')
            comparison=dict(candidate_gross_price=rational(price),matching_segment_count=len(predictions),
                predicted_closing_cost=rational(predicted_cost),replayed_closing_cost=rational(actual_cost),
                predicted_net_cash_profit=rational(predicted_profit),replayed_net_cash_profit=rational(actual_profit),
                cash_profit_difference=rational(_bounded(actual_profit-predicted_profit)),
                gross_contributions=investor['gross_contributions'],gross_distributions=investor['gross_distributions'],equity_multiple=investor['equity_multiple'],
                annual_irr_roots=investor['annual_irr_roots'],selected_IRR=None,upstream_story_blockers=investor['story_blockers'])
        except ArithmeticBudgetError:blockers.append('recovery_case_exact_arithmetic_budget_exceeded');comparison=None
    result={'component':'T53','purpose':'synthetic_recovery_curve_against_independent_full_case_replay',
        'engine_sha256':ENGINE_SHA256,'definition_sha256':hashlib.sha256(DEFINITION_PATH.read_bytes()).hexdigest(),
        'reference_bounded_run_sha256':reference_run.sha256,'recovery_spec_sha256':hashlib.sha256(recovery_spec_raw).hexdigest(),
        'recovery_run_sha256':recovery_run.sha256,'candidate_bounded_run_sha256':candidate_run.sha256,
        'context':p['context'],'currency':p['currency'],'comparison':comparison,
        'state':'matched_synthetic_full_case'if comparison is not None and not blockers else'blocked','blockers':sorted(set(blockers)),
        'reference_recovery_blockers':p['blockers'],'candidate_calculation_blockers':candidate_run.payload['blockers'],
        'candidate_original_cost_blockers':candidate_run.payload['original_cost_blockers'],
        'candidate_inputs_automatically_tuned':False,'investment_criterion_adopted':False,'evidence_currency_checked':False,
        'funding_availability_verified':False,'personal_investor_return':None,'decision':'PENDING','real_decisions_enabled':False,'production_authorized':False}
    encoded=canonical(result);return RecoveryCaseCheckRun(encoded,digest(encoded))


def verify_recovery_case(reference_arguments,reference_run,recovery_spec_raw,recovery_run,candidate_arguments,candidate_run,report):
    if type(report)is not RecoveryCaseCheckRun or digest(report.payload_json)!=report.sha256:raise ValidationError('typed case-check report with matching hash required')
    if check_recovery_case(reference_arguments,reference_run,recovery_spec_raw,recovery_run,candidate_arguments,candidate_run)!=report:raise ValidationError('recovery case-check replay mismatch')
    return report
