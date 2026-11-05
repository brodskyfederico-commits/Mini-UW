"""T105 dated hypothetical cash-risk observations, without a liquidity/ownership claim."""
from dataclasses import dataclass
from fractions import Fraction as F
from pathlib import Path
import json
from .drafts import ValidationError,canonical,digest
from .scheduled_expense_case import sha
from .debt_service import _fraction,rational
from .investor_returns import _date,CATEGORIES
from .operating_noi import _bounded,ArithmeticBudgetError
from .cash_participation import CashParticipationRun
from .cash_participation_artifacts import recover_cash_participation_bundle,ENGINE_SHA256 as SOURCE_ENGINE_SHA256
from .cash_risk import ENGINE_SHA256 as PROJECT_RISK_ENGINE_SHA256,DEFINITION_PATH as PROJECT_RISK_DEFINITION

ENGINE_SHA256=sha(Path(__file__).read_bytes())
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T105.md'
ADDITIVE=('gross_contributions','gross_distributions','net_cash_profit','cash_shortfall_at_horizon','cash_surplus_at_horizon',
    'peak_cumulative_net_equity_funding_at_date_close','possible_intraday_peak_upper_bound','net_sale_distribution',
    'receipts_excluding_sale_distributions','cash_shortfall_excluding_sale_receipts','additional_capital_contributions','refinance_cash_in_contributions')
DATED=('gross_contributions','gross_distributions','cumulative_before_date','cumulative_contributions_less_distributions',
    'within_date_peak_lower_bound','within_date_peak_upper_bound')


def _cash_observations(events,dated_net):
    if type(dated_net)is not list or not 2<=len(dated_net)<=65:raise ValidationError('bounded complete dated net grid required')
    dates=[r['date']for r in dated_net]
    if len(set(dates))!=len(dates)or dates!=sorted(dates):raise ValidationError('strict supplied date order required, no sorting')
    for day in dates:_date(day)
    if type(events)is not list or len(events)>256 or len({e['event_id']for e in events})!=len(events):raise ValidationError('bounded unique gross event inventory required')
    gross={d:[F(0),F(0),[]]for d in dates};totals={k:F(0)for values in CATEGORIES.values()for k in values}
    for index,event in enumerate(events):
        value=_fraction(event['amount'],1300);kind=event['kind'];category=event['category']
        if value is None or value<0 or kind not in CATEGORIES or category not in CATEGORIES[kind]or event['date']not in gross:
            raise ValidationError('known nonnegative classified gross event on supplied grid required')
        bucket=gross[event['date']];which=0 if kind=='contribution'else 1
        bucket[which]=_bounded(bucket[which]+value);bucket[2].append(index);totals[category]=_bounded(totals[category]+value)
    balance=close_peak=upper_peak=a=d=F(0);rows=[]
    for expected in dated_net:
        day=expected['date'];contributions,distributions,indices=gross[day];net=_fraction(expected['net'],1300)
        if net is None or net!=_bounded(distributions-contributions):raise ValidationError('dated gross/net identity differs')
        before=balance;upper=max(F(0),_bounded(before+contributions));balance=_bounded(_bounded(before+contributions)-distributions)
        lower=max(F(0),before,balance);close_peak=max(close_peak,balance);upper_peak=max(upper_peak,upper)
        a=_bounded(a+contributions);d=_bounded(d+distributions)
        rows.append(dict(date=day,gross_contributions=rational(contributions),gross_distributions=rational(distributions),
            cumulative_before_date=rational(before),cumulative_contributions_less_distributions=rational(balance),
            within_date_peak_lower_bound=rational(lower),within_date_peak_upper_bound=rational(upper),
            event_indices=indices,event_ids=[events[i]['event_id']for i in indices]))
    sale=totals['net_sale_distribution'];q=rational
    metrics=dict(gross_contributions=q(a),gross_distributions=q(d),net_cash_profit=q(_bounded(d-a)),
        cash_shortfall_at_horizon=q(max(F(0),balance)),cash_surplus_at_horizon=q(max(F(0),-balance)),
        peak_cumulative_net_equity_funding_at_date_close=q(close_peak),possible_intraday_peak_upper_bound=q(upper_peak),
        net_sale_distribution=q(sale),sale_share_of_distributions=q(_bounded(sale/d))if d>0 else None,
        sale_share_state='computed_synthetic'if d>0 else'undefined_zero_distributions',
        receipts_excluding_sale_distributions=q(_bounded(d-sale)),cash_shortfall_excluding_sale_receipts=q(max(F(0),_bounded(a-_bounded(d-sale)))),
        additional_capital_contributions=q(totals['additional_capital']),refinance_cash_in_contributions=q(totals['refinance_cash_in']))
    return metrics,rows


def _observe_all(parent):
    p=parent.payload;parts=p['participants'];story=parent.parent_run.payload['current_project_return_story']
    project,project_dates=_cash_observations(story['dated_events'],parent.parent_run.payload['irr_recalculation']['dated_net_flows'])
    if project!=story['risk_observations']:raise ValidationError('project cash observations differ from unchanged T37 result')
    result=[]
    for index,part in enumerate(parts):
        if part['currency']!=story['currency']or part['cash_horizon']!=story['cash_horizon']:raise ValidationError('participant cash currency/window differs from project')
        metrics,dates=_cash_observations(part['dated_events'],part['dated_net_flows'])
        for key in('gross_contributions','gross_distributions','net_cash_profit'):
            if metrics[key]!=part[key]:raise ValidationError('participant gross/net totals differ')
        if sorted(i for row in dates for i in row['event_indices'])!=list(range(len(part['dated_events']))):raise ValidationError('complete event index partition required')
        if [r['date']for r in dates]!=[r['date']for r in project_dates]:raise ValidationError('participant and project date grids differ')
        result.append(dict(participant_id=part['participant_id'],share_fraction=part['share_fraction'],
            currency=part['currency'],cash_horizon=part['cash_horizon'],
            source_participant_pointer='/participants/'+str(index),scope='hypothetical_dated_cash_observations_not_actual_funding',
            metrics=metrics,dated_observations=dates,capital_still_invested=None,retained_equity_value=None,conditional_CoC=None,
            final_economic_capital_loss=None,verified_personal_investor_return=None,actual_liquidity_state='PENDING',
            actual_capital_available=None,within_date_order_verified=False))
    totals={key:rational(_bounded(sum((_fraction(row['metrics'][key],1300)for row in result),F(0))))for key in ADDITIVE}
    if any(totals[key]!=project[key]for key in ADDITIVE):raise ValidationError('constant-share cash risk does not reconcile to project')
    dated=[]
    for index,source in enumerate(project_dates):
        values={key:rational(_bounded(sum((_fraction(row['dated_observations'][index][key],1300)for row in result),F(0))))for key in DATED}
        if any(values[key]!=source[key]for key in DATED):raise ValidationError('constant-share dated bounds do not reconcile to project')
        dated.append(dict(date=source['date'],allocated=values))
    for row in result:
        if _fraction(row['metrics']['gross_distributions'],1300)>0 and row['metrics']['sale_share_of_distributions']!=project['sale_share_of_distributions']:
            raise ValidationError('positive scaled receipts must preserve the project sale ratio')
    return result,dict(scope='constant-share-profile-only-not-general-portfolio-aggregation',project_metrics=project,
        additive_metric_totals=totals,dated_checks=dated,sale_ratios_summed=False,
        positive_receipt_ratios_equal_project=True,all_event_indices_partitioned_once_per_participant=True)


@dataclass(frozen=True)
class ParticipantCashRiskRun:
    payload_json:str
    sha256:str
    parent_run:CashParticipationRun
    @property
    def payload(self):return json.loads(self.payload_json)


def _from_verified_allocation(source_raw,parent):
    p=parent.payload;rows=reconciliation=None;blockers=[]
    if p['participants']is None:blockers=['current_participant_cash_unavailable']
    else:
        try:rows,reconciliation=_observe_all(parent)
        except ArithmeticBudgetError:blockers=['participant_cash_risk_exact_arithmetic_budget_exceeded']
    result=dict(component='T105',purpose='hypothetical_participant_cash_risk_observations',engine_sha256=ENGINE_SHA256,
        definition_sha256=sha(DEFINITION.read_bytes()),source_engine_sha256=SOURCE_ENGINE_SHA256,
        project_risk_engine_sha256=PROJECT_RISK_ENGINE_SHA256,project_risk_definition_sha256=sha(PROJECT_RISK_DEFINITION.read_bytes()),
        source_allocation_bundle_sha256=sha(source_raw),source_allocation_run_sha256=parent.sha256,context=p['context'],
        evaluated_as_of_UTC=parent.parent_run.payload['evaluated_as_of_UTC'],
        state='computed_synthetic_cash_risk_observations'if rows is not None else'PENDING',participants=rows,reconciliation=reconciliation,
        blockers=blockers,upstream_allocation_state=p['state'],upstream_allocation_blockers=p['blockers'],
        original_cash_and_IRR_changed=False,allocation_terms_adopted=False,candidate_or_fraction_selected=False,
        sale_exclusion_is_recomputed_scenario=False,capital_still_invested_derived_from_cash=False,
        actual_funding_or_reinvestment_availability_verified=False,actual_intraday_order_verified=False,
        independent_downside_verified=False,full_risk_analysis_completed=False,verified_personal_investor_return=None,
        verified_personal_investor_return_state='PENDING',financial_publication_authorized=False,
        new_external_PDF_created=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')
    value=canonical(result);return ParticipantCashRiskRun(value,digest(value),parent)


def analyze_participant_cash_risk(source_raw):
    recovered=recover_cash_participation_bundle(source_raw)
    return _from_verified_allocation(source_raw,recovered.run)


def verify_participant_cash_risk(source_raw,run):
    if type(run)is not ParticipantCashRiskRun or analyze_participant_cash_risk(source_raw)!=run:raise ValidationError('participant cash risk differs from complete source-first replay')
    return run
