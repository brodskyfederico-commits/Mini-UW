"""T85 reconstruct the supported synthetic financial route from declarative sources."""
from dataclasses import asdict
from pathlib import Path
import copy
import hashlib

from .drafts import ValidationError, canonical
from .construction_draws import produce_construction_draws
from .construction_cash import ConstructionLoanEvidence, assemble_construction_cash
from .construction_bundle import export_construction_bundle
from .operating_debt_phase import produce_operating_debt_phase
from .operating_noi import produce_operating_noi
from .operating_cash import reconcile_operating_cash
from .holding_cash import OperatingPeriodEvidence, reconcile_holding_cash
from .closing_cash import produce_closing_cash
from .debt_closing import DatedLoanEvidence, reconcile_debt_closing
from .debt_service import DateWindow, produce_debt_service
from .project_cash import CheckedClosingEvidence
from .hold_sale_cash import reconcile_hold_sale_cash
from .staged_operating_window import reconcile_staged_operating_window
from .staged_lifecycle_returns import assemble_staged_lifecycle_returns
from .staged_lifecycle_bundle import export_staged_lifecycle_bundle
from .expense_cash_detail import reconcile_expense_cash_detail
from .expense_checked_lifecycle import assemble_expense_checked_lifecycle, export_expense_checked_bundle
from .phased_rental import produce_phased_rental
from .phased_rental_lifecycle import assemble_phased_rental_lifecycle, export_phased_rental_bundle
from .current_phased_rental import assemble_current_phased_rental
from .evidence_currency import evaluate_evidence_currency

ENGINE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
RECIPE_KEYS = {'construction_loans','preopening_source','construction_binding','phase_contract','operating_periods',
               'holding_manifest','sale','hold_sale_binding','cash_boundary_binding','window_binding',
               'investor_source','investor_binding','expense_manifest','rental_manifest'}


def raw(value):
    try:
        return canonical(value).encode('utf-8')
    except UnicodeError as error:
        raise ValidationError('invalid source UTF-8') from error


def sha(value):
    return hashlib.sha256(value).hexdigest()


def linked(source, **technical):
    if type(source) is not dict or set(source) & set(technical):
        raise ValidationError('computed linkage fields must not be supplied or overridden')
    return dict(copy.deepcopy(source), **technical)


class ProjectionBlocked(ValidationError):
    def __init__(self, stage, reasons):
        super().__init__(stage)
        self.stage, self.reasons = stage, reasons


def construct_projection(recipe, registry, as_of):
    if type(recipe) is not dict or set(recipe) != RECIPE_KEYS:
        raise ValidationError('exact v1 declarative source sections required')
    r = copy.deepcopy(recipe)
    stages = []
    def check(name, run, state):
        p = run.payload
        stages.append(dict(stage=name, run_sha256=run.sha256, state=p.get('state',p.get('calculation_status'))))
        if p.get('state',p.get('calculation_status')) != state:
            raise ProjectionBlocked(name, p.get('blockers') or ['producer_not_compatible'])
    try:
        loans = tuple(ConstructionLoanEvidence(raw=raw(s),run=produce_construction_draws(raw(s))) for s in r['construction_loans'])
        pre_raw = raw(r['preopening_source'])
        cb = linked(r['construction_binding'], preopening_source_sha256=sha(pre_raw), loans=[dict(loan_id=e.run.payload['loan_id'],source_sha256=sha(e.raw),run_sha256=e.run.sha256) for e in loans])
        cr = raw(cb)
        construction = assemble_construction_cash(loans,pre_raw,cr)
        check('construction_cash',construction,'reconciled_synthetic_staged_preopening_cash')
        construction_bundle = export_construction_bundle(loans,pre_raw,cr,construction)
        loan_by_id = {e.run.payload['loan_id']:e for e in loans}
        phase_claim = r['phase_contract']
        rows = []
        for s in phase_claim['loan_phases']:
            e = loan_by_id.get(s['loan_id'])
            if e is None:
                raise ProjectionBlocked('operating_phase',['unknown_construction_loan'])
            source = s.pop('schedule_source')
            rows.append(linked(s,construction_loan_source_sha256=sha(e.raw),construction_loan_run_sha256=e.run.sha256,schedule_source_utf8=raw(source).decode()))
        phase_claim['loan_phases'] = rows
        phase_raw = raw(linked(phase_claim,construction_bundle_sha256=sha(construction_bundle),construction_cash_run_sha256=construction.sha256))
        phase = produce_operating_debt_phase(construction_bundle,phase_raw)
        check('operating_phase',phase,'matched_synthetic_same_liability_operating_phase')
        periods, details, calendars = [], {}, {}
        for s in r['operating_periods']:
            if type(s) is not dict or set(s) != {'noi_source','cash_source','expense_detail','rental_calendar'}:
                raise ValidationError('exact v1 per-period sources required')
            nr = raw(s['noi_source']); noi = produce_operating_noi(nr)
            check('NOI:'+s['noi_source']['period_ref'],noi,'computed_synthetic_profile')
            sr = raw(linked(s['cash_source'],noi_source_sha256=sha(nr),noi_run_sha256=noi.sha256))
            cash = reconcile_operating_cash(nr,noi,sr)
            check('operating_cash:'+cash.payload['period_ref'],cash,'reconciled_synthetic_plan')
            e = OperatingPeriodEvidence(noi_raw=nr,noi_run=noi,spec_raw=sr,cash_run=cash)
            periods.append(e)
            pid = cash.payload['period_ref']
            if pid in details:
                raise ValidationError('duplicate v1 operating period')
            dr = raw(linked(s['expense_detail'],noi_source_sha256=sha(nr),noi_run_sha256=noi.sha256,cash_source_sha256=sha(sr),cash_run_sha256=cash.sha256))
            detail = reconcile_expense_cash_detail(nr,noi,sr,cash,dr)
            check('expense_detail:'+pid,detail,'matched_synthetic_expense_cash_detail')
            details[pid] = dict(period_ref=pid,detail_source_utf8=dr.decode(),detail_run=asdict(detail))
            calendar = s['rental_calendar']
            for segment in calendar['segments']:
                source = segment.pop('rental_source')
                if 'rental_source_utf8' in segment:
                    raise ValidationError('nested source has duplicate representation')
                segment['rental_source_utf8'] = raw(source).decode()
            rr = raw(calendar); rent = produce_phased_rental(rr)
            check('phased_rental:'+pid,rent,'computed_synthetic_phased_rental')
            calendars[pid] = (rr,rent)
        periods = tuple(periods)
        by_period = {e.cash_run.payload['period_ref']:e for e in periods}
        manifest = r['holding_manifest']
        for row in manifest['periods']:
            e = by_period.get(row['period_ref'])
            if e is None:
                raise ProjectionBlocked('holding_inventory',['unknown_operating_period'])
            row.update(linked(row,noi_source_sha256=sha(e.noi_raw),noi_run_sha256=e.noi_run.sha256,spec_source_sha256=sha(e.spec_raw),cash_run_sha256=e.cash_run.sha256))
        hr = raw(manifest); holding = reconcile_holding_cash(periods,hr)
        check('holding_cash',holding,'reconciled_synthetic_operating_chain')
        sale = r['sale']
        if type(sale) is not dict or set(sale) != {'closing_id','closing_source','debt_binding'}:
            raise ValidationError('exact v1 sale source fields required')
        sale_raw = raw(sale['closing_source']); closing = produce_closing_cash(sale_raw)
        check('sale_cash',closing,'computed_synthetic_closing')
        operating_loans = phase.operating_loans
        debt_claim = sale['debt_binding']
        expected = {e.run.payload['loan_id']:e for e in operating_loans}
        for row in debt_claim['loans']:
            e = expected.get(row['loan_id'])
            if e is None:
                raise ProjectionBlocked('sale_debt',['unknown_operating_loan'])
            row.update(linked(row,loan_source_sha256=sha(e.loan_raw),loan_run_sha256=e.run.sha256))
        dr = raw(linked(debt_claim,closing_source_sha256=sha(sale_raw),closing_run_sha256=closing.sha256))
        debt = reconcile_debt_closing(operating_loans,sale_raw,closing,dr)
        check('sale_debt',debt,'matched_synthetic_debt_assumptions')
        closing_evidence = CheckedClosingEvidence(closing_id=sale['closing_id'],closing_raw=sale_raw,closing_run=closing,loans=operating_loans,debt_spec_raw=dr,debt_run=debt)
        hs = raw(linked(r['hold_sale_binding'],holding_source_sha256=sha(hr),holding_run_sha256=holding.sha256,sale_source_sha256=sha(sale_raw),sale_run_sha256=closing.sha256,debt_binding_source_sha256=sha(dr),debt_run_sha256=debt.sha256))
        ha = (periods,closing_evidence,hr,holding,hs)
        hold = reconcile_hold_sale_cash(*ha)
        check('hold_sale',hold,'reconciled_synthetic_no_refinance_cash')
        first = by_period[manifest['periods'][0]['period_ref']]
        boundary = raw(linked(r['cash_boundary_binding'],preopening_source_sha256=sha(construction.compiled_raw),preopening_run_sha256=construction.preopening_run.sha256,operating_source_sha256=sha(first.spec_raw),operating_run_sha256=first.cash_run.sha256))
        ws = raw(linked(r['window_binding'],construction_bundle_sha256=sha(construction_bundle),phase_run_sha256=phase.sha256,holding_manifest_sha256=sha(hr),hold_sale_spec_sha256=sha(hs),hold_sale_run_sha256=hold.sha256,cash_binding_sha256=sha(boundary)))
        wa = (construction_bundle,phase_raw,phase,ha,hold,boundary,ws)
        window = reconcile_staged_operating_window(*wa)
        check('staged_operating_window',window,'matched_synthetic_staged_operating_window')
        ir = raw(r['investor_source'])
        ib = raw(linked(r['investor_binding'],window_run_sha256=window.sha256,investor_source_sha256=sha(ir)))
        returns = assemble_staged_lifecycle_returns(wa,window,ir,ib)
        check('lifecycle_return',returns,'compiled_synthetic_staged_purchase_to_sale')
        life_bundle = export_staged_lifecycle_bundle(wa,window,ir,ib,returns)
        em = r['expense_manifest']
        if any(type(row)is not dict or set(row)!={'period_ref'}for row in em['periods']):
            raise ValidationError('expense manifest accepts only declared period IDs; no supplied result overrides')
        em['periods'] = [details[row['period_ref']] for row in em['periods']]
        em_raw = raw(linked(em,lifecycle_bundle_sha256=sha(life_bundle)))
        expense = assemble_expense_checked_lifecycle(life_bundle,em_raw)
        check('expense_checked_return',expense,'compiled_synthetic_expense_checked_lifecycle')
        eb = export_expense_checked_bundle(life_bundle,em_raw,expense)
        rm = r['rental_manifest']
        for row in rm['periods']:
            pid = row['period_ref']; e = by_period[pid]; rr,rent = calendars[pid]
            row.update(linked(row,calendar_source_utf8=rr.decode(),calendar_run=asdict(rent),noi_source_sha256=sha(e.noi_raw),cash_source_sha256=sha(e.spec_raw)))
        rm_raw = raw(linked(rm,expense_bundle_sha256=sha(eb)))
        phased = assemble_phased_rental_lifecycle(eb,rm_raw)
        check('phased_rental_return',phased,'compiled_synthetic_phased_rental_lifecycle')
        bundle = export_phased_rental_bundle(eb,rm_raw,phased)
        registry_raw = raw(registry)
        currency = evaluate_evidence_currency(registry_raw,as_of)
        current = assemble_current_phased_rental(bundle,registry_raw,currency,as_of)
        stages.append(dict(stage='source_currency',run_sha256=current.sha256,state=current.payload['state']))
        return dict(bundle=bundle,current=current.payload,stages=stages,blockers=[])
    except ProjectionBlocked as error:
        return dict(bundle=None,current=None,stages=stages,blockers=[error.stage+':'+str(s) for s in error.reasons])
