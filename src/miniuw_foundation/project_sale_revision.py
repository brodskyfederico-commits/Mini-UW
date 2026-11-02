"""T39 explicit sale proceeds/cost source revision through the guarded cash chain."""
from dataclasses import dataclass, asdict, replace
from pathlib import Path
import hashlib
import json
import re

from .drafts import ValidationError, canonical, digest, nonempty
from .intake import _unique_object, _invalid_constant
from .debt_service import _fraction
from .investor_returns import _date
from .closing_cash import parse_closing_cash, produce_closing_cash
from .debt_closing import reconcile_debt_closing
from .holding_cash import OperatingPeriodEvidence
from .project_cash import CheckedClosingEvidence, ProjectCashRun, reconcile_project_cash
from .refinance_capacity import RefinanceInputs, RefinanceCapacityRun
from .capacity_project_returns import (CapacityProjectBinding, CapacityProjectReturnRun,
                                       assemble_capacity_checked_returns)
from .cash_risk import summarize_cash_risk

ENGINE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION_PATH = Path(__file__).resolve().parents[2] / 'docs/technical-implementation-T39-T40.md'


@dataclass(frozen=True)
class CapacityProjectEvidence:
    periods: tuple[OperatingPeriodEvidence, ...]
    closings: tuple[CheckedClosingEvidence, ...]
    manifest_raw: bytes
    project_run: ProjectCashRun
    capacity_inputs: RefinanceInputs
    capacity_spec_raw: bytes
    capacity_run: RefinanceCapacityRun
    investor_raw: bytes
    binding: CapacityProjectBinding
    guarded_run: CapacityProjectReturnRun

    def arguments(self):
        return (self.periods, self.closings, self.manifest_raw, self.project_run,
                self.capacity_inputs, self.capacity_spec_raw, self.capacity_run,
                self.investor_raw, self.binding)


def verify_evidence(evidence):
    if type(evidence) is not CapacityProjectEvidence:
        raise ValidationError('typed immutable capacity-checked project evidence required')
    if assemble_capacity_checked_returns(*evidence.arguments()) != evidence.guarded_run:
        raise ValidationError('complete capacity-checked project source/run replay mismatch')


def evidence_fingerprint(evidence):
    """Source/run identity; caller must also verify complete upstream reproduction."""
    if type(evidence) is not CapacityProjectEvidence:
        raise ValidationError('typed project evidence required')
    sha = lambda raw: hashlib.sha256(raw).hexdigest()
    i = evidence.capacity_inputs
    sources = {
        'periods': [[sha(p.noi_raw), p.noi_run.sha256, sha(p.spec_raw), p.cash_run.sha256]
                    for p in evidence.periods],
        'closings': [[c.closing_id, sha(c.closing_raw), c.closing_run.sha256,
                     sha(c.debt_spec_raw), c.debt_run.sha256,
                     [[sha(l.loan_raw), l.run.sha256] for l in c.loans]] for c in evidence.closings],
        'manifest': sha(evidence.manifest_raw), 'project_run': evidence.project_run.sha256,
        'capacity_inputs': [sha(i.valuation_noi_raw), i.valuation_noi_run.sha256,
            sha(i.bank_noi_raw), i.bank_noi_run.sha256, sha(i.new_loan.loan_raw), i.new_loan.run.sha256,
            sha(i.closing_raw), i.closing_run.sha256],
        'capacity_spec': sha(evidence.capacity_spec_raw), 'capacity_run': evidence.capacity_run.sha256,
        'investor_source': sha(evidence.investor_raw), 'binding': asdict(evidence.binding),
        'guarded_run': evidence.guarded_run.sha256}
    return digest(canonical(sources))


def parse_sale_revision(raw):
    if type(raw) is not bytes or not raw or len(raw) > 131072:
        raise ValidationError('bounded explicit sale source revision required')
    try:
        p = json.loads(raw.decode(), object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ValidationError('invalid sale revision JSON') from error
    if type(p) is not dict or set(p) != {'schema', 'revision_id', 'base_evidence_sha256',
            'sale_node_id', 'unchanged_other_sources_basis_ref', 'equity_funding_assumption_ref',
            'replacement_claims'} or p['schema'] != 'miniuw.synthetic-project-sale-source-revision.v1':
        raise ValidationError('exact sale source revision profile required')
    for key in ['revision_id', 'sale_node_id']:
        nonempty(p[key], key)
    if type(p['base_evidence_sha256']) is not str or not re.fullmatch('[a-f0-9]{64}', p['base_evidence_sha256']):
        raise ValidationError('exact base evidence hash required')
    for key in ['unchanged_other_sources_basis_ref', 'equity_funding_assumption_ref']:
        if p[key] is not None:
            nonempty(p[key], key)
    if type(p['replacement_claims']) is not dict or set(p['replacement_claims']) != {'gross_proceeds', 'closing_costs_paid'}:
        raise ValidationError('explicit gross proceeds and closing cost claims required')
    for claim in p['replacement_claims'].values():
        if type(claim) is not dict or set(claim) != {'value', 'currency', 'as_of_date', 'basis', 'source_ref'}:
            raise ValidationError('exact dated monetary claim required')
        _fraction(claim['value'])
        for key in ['currency', 'basis', 'source_ref']:
            if claim[key] is not None:
                nonempty(claim[key], key)
        if claim['as_of_date'] is not None:
            _date(claim['as_of_date'])
    return p


@dataclass(frozen=True)
class ProjectSaleRevisionRun:
    payload_json: str
    sha256: str

    @property
    def payload(self):
        return json.loads(self.payload_json)

    @property
    def guarded_run(self):
        p = self.payload['guarded_run']
        return None if p is None else CapacityProjectReturnRun(**p)


def _revise(evidence, spec_raw):
    spec = parse_sale_revision(spec_raw)
    verify_evidence(evidence)
    fingerprint = evidence_fingerprint(evidence)
    blockers = []
    if spec['base_evidence_sha256'] != fingerprint:
        blockers.append('base_evidence_sha256_mismatch')
    if spec['unchanged_other_sources_basis_ref'] is None:
        blockers.append('explicit_unchanged_other_sources_assumption_missing')
    matching = [c for c in evidence.closings if c.closing_id == spec['sale_node_id']]
    sale = matching[0] if len(matching) == 1 else None
    if sale is None or parse_closing_cash(sale.closing_raw)['kind'] != 'sale':
        blockers.append('exact_sale_closing_not_identified')
    nodes = json.loads(evidence.manifest_raw)['nodes']
    if not any(n['node_id'] == spec['sale_node_id'] and n['kind'] == 'sale' for n in nodes):
        blockers.append('sale_node_not_present_in_manifest')
    revised = None; cr = br = mr = None; closing = debt = project = guarded = risk = None
    changes = []
    if not blockers:
        source = parse_closing_cash(sale.closing_raw)
        for field, claim in spec['replacement_claims'].items():
            changes.append({'locator': '/amounts/' + field, 'before': source['amounts'][field], 'after': claim})
            source['amounts'][field] = claim
        changes.append({'locator': '/equity_funding_assumption_ref',
                        'before': source['equity_funding_assumption_ref'],
                        'after': spec['equity_funding_assumption_ref']})
        source['equity_funding_assumption_ref'] = spec['equity_funding_assumption_ref']
        cr = canonical(source).encode()
        closing = produce_closing_cash(cr)
        debt_spec = json.loads(sale.debt_spec_raw)
        debt_spec.update(closing_source_sha256=hashlib.sha256(cr).hexdigest(), closing_run_sha256=closing.sha256)
        br = canonical(debt_spec).encode()
        debt = reconcile_debt_closing(sale.loans, cr, closing, br)
        new_sale = CheckedClosingEvidence(closing_id=sale.closing_id, closing_raw=cr, closing_run=closing,
            loans=sale.loans, debt_spec_raw=br, debt_run=debt)
        closings = tuple(new_sale if c.closing_id == sale.closing_id else c for c in evidence.closings)
        manifest = json.loads(evidence.manifest_raw)
        node = next(n for n in manifest['nodes'] if n['node_id'] == sale.closing_id)
        node.update(source_sha256=hashlib.sha256(cr).hexdigest(), run_sha256=closing.sha256,
                    upstream_source_sha256=hashlib.sha256(br).hexdigest(), upstream_run_sha256=debt.sha256)
        mr = canonical(manifest).encode()
        project = reconcile_project_cash(evidence.periods, closings, mr)
        inner = replace(evidence.binding.project_return_binding,
            manifest_source_sha256=hashlib.sha256(mr).hexdigest(), project_run_sha256=project.sha256)
        binding = replace(evidence.binding, project_return_binding=inner)
        guarded = assemble_capacity_checked_returns(evidence.periods, closings, mr, project,
            evidence.capacity_inputs, evidence.capacity_spec_raw, evidence.capacity_run,
            evidence.investor_raw, binding)
        revised = replace(evidence, closings=closings, manifest_raw=mr, project_run=project,
                          binding=binding, guarded_run=guarded)
        blockers.extend(guarded.payload['blockers'])
        if guarded.compiled_raw is not None:
            risk = summarize_cash_risk(guarded.compiled_raw, guarded.investor_run)
            if risk.payload['state'] != 'computed_synthetic':
                blockers.extend(risk.payload['cash_blockers'])
    payload = {
        'component': 'T39', 'purpose': 'synthetic_sale_source_revision_through_capacity_checked_project',
        'engine_sha256': ENGINE_SHA256,
        'definition_sha256': hashlib.sha256(DEFINITION_PATH.read_bytes()).hexdigest(),
        'spec_sha256': hashlib.sha256(spec_raw).hexdigest(), 'revision_id': spec['revision_id'],
        'base_evidence_sha256': fingerprint,
        'revised_evidence_sha256': None if revised is None else evidence_fingerprint(revised),
        'state': 'compiled_synthetic' if guarded is not None and guarded.compiled_raw is not None and not blockers else 'blocked',
        'changes': changes, 'blockers': sorted(set(blockers)),
        'revised_closing_json': None if cr is None else cr.decode(),
        'revised_debt_spec_json': None if br is None else br.decode(),
        'revised_manifest_json': None if mr is None else mr.decode(),
        'closing_run': None if closing is None else asdict(closing),
        'debt_run': None if debt is None else asdict(debt),
        'project_run': None if project is None else asdict(project),
        'guarded_run': None if guarded is None else asdict(guarded),
        'risk_run': None if risk is None else asdict(risk),
        'capacity_source_and_run_unchanged': True,
        'context_preserved_source_revision_not_new_market_scenario': True,
        'other_sources_explicitly_frozen': spec['unchanged_other_sources_basis_ref'] is not None,
        'all_revised_producers_replayed': revised is not None,
        'complete_market_scenario_recomputed': False,
        'bank_credit_approved': False, 'actual_funding_available': False,
        'personal_investor_return': None, 'final_economic_capital_loss': None,
        'decision': 'PENDING', 'real_decisions_enabled': False, 'production_authorized': False}
    encoded = canonical(payload)
    return ProjectSaleRevisionRun(encoded, digest(encoded)), revised


def revise_project_sale(evidence, spec_raw):
    return _revise(evidence, spec_raw)[0]


def recover_sale_revision(evidence, spec_raw, report):
    """Reproduce supplied source evidence before returning the revised typed chain."""
    if type(report) is not ProjectSaleRevisionRun or digest(report.payload_json) != report.sha256:
        raise ValidationError('typed sale revision report with matching hash required')
    replay, revised = _revise(evidence, spec_raw)
    if replay != report:
        raise ValidationError('sale source revision report replay mismatch')
    return revised
