"""T108 one explicit source entry: staged opening, T76 cash/stocks, settled sale, returns."""
from dataclasses import dataclass
from pathlib import Path
import copy,json
from .drafts import ValidationError,canonical,digest
from .expense_cash_detail import _json,_exact
from .expense_checked_lifecycle import _utf8
from .scheduled_expense_case import sha
from .lifecycle_bundle import _loan
from .operating_debt_phase import produce_operating_debt_phase
from .operating_noi import produce_operating_noi
from .operating_cash import reconcile_operating_cash
from .holding_cash import OperatingPeriodEvidence,reconcile_holding_cash
from .closing_cash import produce_closing_cash
from .debt_closing import reconcile_debt_closing
from .project_cash import CheckedClosingEvidence
from .settled_hold_sale import reconcile_settled_hold_sale_cash
from .settled_operating_window import reconcile_settled_operating_window
from .settled_lifecycle_returns import assemble_settled_lifecycle_returns
from .primitive_periodic_returns import isolate_primitive_periodic_returns,ENGINE_SHA256 as PRIMITIVE_ENGINE_SHA256
from .irr_checked_output import _current_annual_roots,IRR_BLOCKER
from .debt_service import _fraction

ENGINE_SHA256=sha(Path(__file__).read_bytes())
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T108.md'
MAX_SOURCE_BYTES=16*1024*1024


def parse_settled_case(raw):
    p=_json(raw,MAX_SOURCE_BYTES);_exact(p,{'schema','construction_bundle_utf8','phase_source_utf8','periods','sale','holding_source_utf8',
        'hold_sale_source_utf8','boundary_source_utf8','cash_boundary_source_utf8','window_source_utf8','investor_source_utf8','return_binding_source_utf8'})
    if p['schema']!='miniuw.synthetic-settled-lifecycle-case.v1':raise ValidationError('exact synthetic settled lifecycle case required')
    for key in set(p)-{'schema','periods','sale'}:_utf8(p[key],8*1024*1024 if key in('construction_bundle_utf8','boundary_source_utf8')else 1048576)
    if type(p['periods'])is not list or not 1<=len(p['periods'])<=64:raise ValidationError('one to64 explicit period sources required')
    for row in p['periods']:
        _exact(row,{'noi_source_utf8','cash_source_utf8'})
        for value in row.values():_utf8(value,1048576)
    _exact(p['sale'],{'closing_id','closing_source_utf8','loans','debt_source_utf8'})
    if type(p['sale']['loans'])is not list or len(p['sale']['loans'])>32:raise ValidationError('bounded explicit loan source records required')
    return p


def source_window(p):
    construction=p['construction_bundle_utf8'].encode();phase_raw=p['phase_source_utf8'].encode();phase=produce_operating_debt_phase(construction,phase_raw);periods=[]
    for row in p['periods']:
        nr=row['noi_source_utf8'].encode();cr=row['cash_source_utf8'].encode();noi=produce_operating_noi(nr)
        periods.append(OperatingPeriodEvidence(noi_raw=nr,noi_run=noi,spec_raw=cr,cash_run=reconcile_operating_cash(nr,noi,cr)))
    periods=tuple(periods);s=p['sale'];cr=_utf8(s['closing_source_utf8'],1048576);dr=_utf8(s['debt_source_utf8'],1048576);closing=produce_closing_cash(cr);loans=tuple(_loan(row)for row in s['loans'])
    sale=CheckedClosingEvidence(closing_id=s['closing_id'],closing_raw=cr,closing_run=closing,loans=loans,debt_spec_raw=dr,debt_run=reconcile_debt_closing(loans,cr,closing,dr))
    hr=p['holding_source_utf8'].encode();holding=reconcile_holding_cash(periods,hr);ha=(periods,sale,hr,holding,p['hold_sale_source_utf8'].encode(),p['boundary_source_utf8'].encode());hold=reconcile_settled_hold_sale_cash(*ha)
    wa=(construction,phase_raw,phase,ha,hold,p['cash_boundary_source_utf8'].encode(),p['window_source_utf8'].encode());window=reconcile_settled_operating_window(*wa)
    return wa,window


@dataclass(frozen=True)
class SettledCaseRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def assemble_settled_case(raw):
    p=parse_settled_case(raw);wa,window=source_window(p);ir=p['investor_source_utf8'].encode();br=p['return_binding_source_utf8'].encode();run=assemble_settled_lifecycle_returns(wa,window,ir,br)
    h=wa[4].payload;boundary=json.loads(h['settlement_boundary_run']['payload_json']);r=run.payload;story=None;irr_evidence=None
    if run.investor_run is not None:
        story=copy.deepcopy(run.investor_run.payload);source=json.loads(run.compiled_raw);params=source['irr_parameters']
        roots=isolate_primitive_periodic_returns([_fraction(row['net'],1300)for row in story['dated_net_flows']],_fraction(params['max_periodic_rate_interval_width']),params['split_budget'],params['operation_budget'])
        annual,attempted,issues=_current_annual_roots(roots,params['periods_per_year'],source['grid']['step_months'])
        unique=roots['status']=='complete_synthetic'and roots['distinct_positive_discount_roots']==1
        story.update(component='T108-project-story',engine_sha256=ENGINE_SHA256,root_engine_sha256=PRIMITIVE_ENGINE_SHA256,cash_engine_run_sha256=run.investor_run.sha256)
        story['periodic_irr']=roots;story['annual_irr_roots']=annual;story['selected_IRR']=None
        story['story_blockers']=sorted(set([b for b in story['story_blockers']if b!=IRR_BLOCKER]+issues+([]if unique else[IRR_BLOCKER])))
        story['declared_cash_story_computable']=not story['story_blockers'];story['cash_projection_producers_connected']=True
        irr_evidence=dict(parameters=params,grid=source['grid'],primitive_roots=roots,annual_roots=annual,attempted_annual_roots=attempted,
            annualization_blockers=issues,source_cash_run_sha256=run.investor_run.sha256,point_rate_selected=False)
    result=dict(component='T108',scope='synthetic_staged_opening_operating_expense_stocks_settled_sale_and_project_equity_return',
        engine_sha256=ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),source_sha256=sha(raw),context=window.payload['context'],currency=window.payload['currency'],
        source_run_hashes=dict(phase=wa[2].sha256,holding=wa[3][3].sha256,settlement=h['settlement_boundary_run']['sha256'],hold_sale=wa[4].sha256,window=window.sha256,returns=run.sha256),
        settlement_summary=boundary['summary']if story is not None else None,operating_totals=wa[3][3].payload['totals']if story is not None else None,
        holding_sale_totals=h['totals']if story is not None else None,cash_conservation_residual=h['cash_conservation_residual']if story is not None else None,
        project_return_story=story,compiled_investor_json=None if story is None else run.compiled_raw.decode(),irr_evidence=irr_evidence,
        cash_risk_run=r['cash_risk_run']if story is not None else None,period_checks=boundary['periods'],item_continuity_checks=boundary['item_continuity_checks'],
        blockers=dict(boundary=boundary['blockers'],holding=h['holding_blockers'],hold_sale=h['blockers'],window=window.payload['blockers'],returns=r['blockers']),
        state='compiled_synthetic_settled_purchase_to_sale'if story is not None else'PENDING',
        accounting_stocks_inferred=False,extra_expense_payment_or_equity_generated=False,phase_principal_counted_as_new_equity=False,
        full_supplied_synthetic_cash_path_connected=story is not None,all_model_profiles_or_financial_validation_complete=False,
        current_source_authority_verified=False,one_page_for_this_new_profile_integrated=False,personal_investor_return=None,
        capital_or_CoC_definitions_adopted=False,new_external_PDF_created=False,financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')
    text=canonical(result);return SettledCaseRun(text,digest(text))


def verify_settled_case(raw,run):
    if type(run)is not SettledCaseRun or assemble_settled_case(raw)!=run:raise ValidationError('settled case differs from complete source-first replay')
    return run
