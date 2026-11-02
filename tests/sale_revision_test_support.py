"""Explicit synthetic source branches; original project/bank fixtures remain unchanged."""
import copy
import json
from miniuw_foundation.debt_service import rational
from fractions import Fraction
from miniuw_foundation.project_cash import reconcile_project_cash
from miniuw_foundation.project_returns import ProjectEventSlot, ProjectReturnBinding
from miniuw_foundation.refinance_capacity import size_refinance
from miniuw_foundation.capacity_project_returns import CapacityProjectBinding, assemble_capacity_checked_returns
from miniuw_foundation.project_sale_revision import CapacityProjectEvidence, evidence_fingerprint
from project_test_support import load_case, build, raw, sha
from capacity_test_support import load_capacity, build_capacity


def make_evidence(compatible=False, sale_contribution_slot=False, project=None, cap=None):
    project = load_case() if project is None else copy.deepcopy(project)
    cap = load_capacity('project') if cap is None else copy.deepcopy(cap)
    if compatible:
        cap['bank']['income_rows'][0]['value'] = rational(Fraction(2000))
        cap['bank']['income_rows'][0]['source_ref'] = 'SYNTHETIC-test-only-distinct-bank-NOI-not-original-project-repair'
    if sale_contribution_slot:
        project['investor']['events'].append(dict(event_id='sale-cash-in', date='2027-07-01', kind='contribution',
            category='additional_capital', amount=None, currency='USD', source_ref=None))
    ops, closes, manifest = build(project); p = reconcile_project_cash(ops, closes, manifest)
    inputs, spec = build_capacity(cap); c = size_refinance(inputs, spec); investor = raw(project['investor'])
    slots = tuple(ProjectEventSlot(node_id=n['node_id'], distribution_event_id=eid,
        contribution_event_id='sale-cash-in' if n['kind']=='sale' and sale_contribution_slot else None)
        for n,eid in zip(json.loads(manifest)['nodes'], ['op-before','refi','op-after','sale']))
    inner = ProjectReturnBinding(profile_id='SYNTHETIC-OPENING-EQUITY-AND-CASH-NODE-EVENTS-v1',
        manifest_source_sha256=sha(manifest), project_run_sha256=p.sha256, investor_source_sha256=sha(investor),
        opening_contribution_event_ids=('initial',), slots=slots)
    binding = CapacityProjectBinding(profile_id='SYNTHETIC-CAPACITY-CHECKED-PROJECT-RETURN-v1',
        capacity_spec_sha256=sha(spec), capacity_run_sha256=c.sha256, refinance_node_id='SYNTHETIC-project-refinance',
        project_return_binding=inner)
    guarded = assemble_capacity_checked_returns(ops, closes, manifest, p, inputs, spec, c, investor, binding)
    return CapacityProjectEvidence(ops, closes, manifest, p, inputs, spec, c, investor, binding, guarded)


def revision(evidence, proceeds=400, costs=20, revision_id='SYNTHETIC-sale-source-revision', funding_ref=None):
    claims = copy.deepcopy(json.loads(evidence.closings[1].closing_raw)['amounts'])
    claims = {k:claims[k] for k in ['gross_proceeds','closing_costs_paid']}
    for key, value in [('gross_proceeds',proceeds),('closing_costs_paid',costs)]:
        claims[key]['value'] = None if value is None else rational(Fraction(value))
        claims[key]['source_ref'] = revision_id+'#/'+key
    return dict(schema='miniuw.synthetic-project-sale-source-revision.v1', revision_id=revision_id,
        base_evidence_sha256=evidence_fingerprint(evidence), sale_node_id=evidence.closings[1].closing_id,
        unchanged_other_sources_basis_ref='SYNTHETIC-unchanged-other-source-hypothesis',
        equity_funding_assumption_ref=funding_ref, replacement_claims=claims)


def inventory(evidence, specs):
    return dict(schema='miniuw.synthetic-project-sale-comparison.v1',base_evidence_sha256=evidence_fingerprint(evidence),
        inventory_declared_complete=True, inventory_basis_ref='SYNTHETIC-explicit-case-inventory',
        revisions=[dict(revision_id=json.loads(s)['revision_id'],spec_sha256=sha(s)) for s in specs])
