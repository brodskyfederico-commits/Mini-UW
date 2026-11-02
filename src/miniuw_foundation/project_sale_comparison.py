"""T40 complete declared inventory of guarded sale source revisions."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import re

from .drafts import ValidationError, canonical, digest, nonempty
from .intake import _unique_object, _invalid_constant
from .project_sale_revision import (parse_sale_revision, verify_evidence, evidence_fingerprint,
                                    revise_project_sale)

ENGINE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEFINITION_PATH = Path(__file__).resolve().parents[2] / 'docs/technical-implementation-T39-T40.md'


def parse_sale_comparison(raw):
    if type(raw) is not bytes or not raw or len(raw) > 65536:
        raise ValidationError('bounded comparison inventory required')
    try:
        p = json.loads(raw.decode(), object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ValidationError('invalid comparison JSON') from error
    if type(p) is not dict or set(p) != {'schema', 'base_evidence_sha256',
            'inventory_declared_complete', 'inventory_basis_ref', 'revisions'} or p['schema'] != 'miniuw.synthetic-project-sale-comparison.v1':
        raise ValidationError('exact comparison inventory profile required')
    if type(p['base_evidence_sha256']) is not str or not re.fullmatch('[a-f0-9]{64}', p['base_evidence_sha256']):
        raise ValidationError('exact base evidence SHA required')
    if p['inventory_declared_complete'] is not None and type(p['inventory_declared_complete']) is not bool:
        raise ValidationError('explicit inventory declaration required')
    if p['inventory_basis_ref'] is not None:
        nonempty(p['inventory_basis_ref'], 'inventory_basis_ref')
    if type(p['revisions']) is not list or not 1 <= len(p['revisions']) <= 12:
        raise ValidationError('one to twelve explicit revisions required')
    seen = set()
    for row in p['revisions']:
        if type(row) is not dict or set(row) != {'revision_id', 'spec_sha256'}:
            raise ValidationError('exact revision identity/hash required')
        nonempty(row['revision_id'], 'revision_id')
        if row['revision_id'] in seen:
            raise ValidationError('duplicate revision identity')
        seen.add(row['revision_id'])
        if type(row['spec_sha256']) is not str or not re.fullmatch('[a-f0-9]{64}', row['spec_sha256']):
            raise ValidationError('exact revision source SHA required')
    return p


@dataclass(frozen=True)
class ProjectSaleComparisonRun:
    payload_json: str
    sha256: str

    @property
    def payload(self):
        return json.loads(self.payload_json)


def compare_project_sales(evidence, revision_specs, inventory_raw):
    inventory = parse_sale_comparison(inventory_raw)
    if type(revision_specs) is not tuple or not 1 <= len(revision_specs) <= 12:
        raise ValidationError('immutable bounded complete revision source inventory required')
    specs = [parse_sale_revision(raw) for raw in revision_specs]
    identities = [s['revision_id'] for s in specs]
    if len(set(identities)) != len(identities):
        raise ValidationError('duplicate supplied revision source identity')
    verify_evidence(evidence)
    fingerprint = evidence_fingerprint(evidence)
    blockers = []
    if inventory['base_evidence_sha256'] != fingerprint:
        blockers.append('comparison_base_evidence_mismatch')
    if inventory['inventory_declared_complete'] is not True or inventory['inventory_basis_ref'] is None:
        blockers.append('comparison_inventory_not_explicitly_complete_with_basis')
    actual = [{'revision_id': s['revision_id'], 'spec_sha256': hashlib.sha256(raw).hexdigest()}
              for s, raw in zip(specs, revision_specs)]
    if actual != inventory['revisions']:
        blockers.append('declared_and_supplied_revision_inventory_mismatch')
    rows = []
    for spec, raw in zip(specs, revision_specs):
        row = {'revision_id': spec['revision_id'], 'spec_sha256': hashlib.sha256(raw).hexdigest(),
               'replacement_claims': spec['replacement_claims'], 'state': 'blocked',
               'revision_run_sha256': None, 'blockers': list(blockers),
               'stage_states': None, 'stage_blockers': None,
               'projected_sale_distribution': None, 'projected_sale_contribution_required': None,
               'cash_metrics': None, 'equity_multiple': None, 'annual_irr_roots': None,
               'selected_IRR': None, 'upstream_story_blockers': None, 'decision': 'PENDING'}
        if not blockers:
            report = revise_project_sale(evidence, raw); p = report.payload
            def stage(name):
                value = p[name]
                return None if value is None else json.loads(value['payload_json'])
            closing = stage('closing_run'); debt = stage('debt_run'); project = stage('project_run')
            guarded = report.guarded_run
            row.update(state=p['state'], revision_run_sha256=report.sha256, blockers=p['blockers'],
                stage_states={'closing': None if closing is None else closing['state'],
                    'debt': None if debt is None else debt['state'],
                    'cash_window': None if project is None else project['state'],
                    'capacity': evidence.capacity_run.payload['state'],
                    'guarded_return': None if guarded is None else guarded.payload['state']},
                stage_blockers={'closing': [] if closing is None else closing['blockers'],
                    'debt': [] if debt is None else debt['blockers'],
                    'cash_window': [] if project is None else project['blockers'],
                    'capacity': evidence.capacity_run.payload['blockers']},
                projected_sale_distribution=None if closing is None else closing['projected_equity_distribution'],
                projected_sale_contribution_required=None if closing is None else closing['projected_equity_contribution_required'])
            if p['state'] == 'compiled_synthetic':
                investor = guarded.investor_run.payload
                risk = stage('risk_run')
                row.update(cash_metrics=risk['metrics'], equity_multiple=investor['equity_multiple'],
                           annual_irr_roots=investor['annual_irr_roots'],
                           upstream_story_blockers=investor['story_blockers'])
        rows.append(row)
    all_compiled = all(r['state'] == 'compiled_synthetic' for r in rows)
    payload = {'component': 'T40', 'purpose': 'synthetic_guarded_project_sale_revision_comparison',
        'engine_sha256': ENGINE_SHA256,
        'definition_sha256': hashlib.sha256(DEFINITION_PATH.read_bytes()).hexdigest(),
        'inventory_sha256': hashlib.sha256(inventory_raw).hexdigest(),
        'base_evidence_sha256': fingerprint,
        'base_guarded_return_state': evidence.guarded_run.payload['state'],
        'base_capacity_blockers': evidence.capacity_run.payload['blockers'],
        'state': 'computed_synthetic_revisions' if all_compiled else 'pending_blocked_revisions',
        'blockers': sorted(set(blockers)), 'revisions': rows,
        'all_declared_revisions_compiled': all_compiled,
        'declared_revision_inventory_verified': not blockers,
        'best_case_selected': False, 'complete_market_scenarios_recomputed': False,
        'downside_policy_adopted': False, 'bank_credit_approved': False,
        'personal_investor_return': None, 'final_economic_capital_loss': None,
        'decision': 'PENDING', 'real_decisions_enabled': False, 'production_authorized': False}
    encoded = canonical(payload)
    return ProjectSaleComparisonRun(encoded, digest(encoded))


def verify_sale_comparison(evidence, revision_specs, inventory_raw, report):
    if type(report) is not ProjectSaleComparisonRun or digest(report.payload_json) != report.sha256:
        raise ValidationError('typed comparison report with matching hash required')
    if compare_project_sales(evidence, revision_specs, inventory_raw) != report:
        raise ValidationError('sale comparison report replay mismatch')
    return report
