import copy
from miniuw_foundation.current_exit_output import required_exit_sources
from miniuw_foundation.evidence_currency import evaluate_evidence_currency
from miniuw_foundation.sale_costs import produce_sale_costs
from miniuw_foundation.costed_exit_sale import assemble_costed_exit_sale
from sale_cost_test_support import evidence,valuation,cost_source,bridge_spec,raw

AS_OF='2027-07-01T12:00:00Z'


def costed_case(compatible=True):
    e=evidence(compatible);nr,n,vr,v=valuation();cr=raw(cost_source(v));c=produce_sale_costs(cr);br=raw(bridge_spec(e,vr,v,cr,c))
    args=(e,nr,n,vr,v,cr,c,br)
    return args,assemble_costed_exit_sale(*args)


def registry(context,requirements):
    p=dict(schema='miniuw.synthetic-evidence-currency.v1',context=copy.deepcopy(context),inventory_declared_complete=True,
        inventory_basis_ref='SYNTHETIC-complete-transport-source-inventory-not-financial-authentication',requirements=copy.deepcopy(requirements),evidence=[])
    for i,req in enumerate(requirements):
        p['evidence'].append(dict(req,evidence_id='SYNTHETIC-evidence-'+str(i),issued_at='2027-06-01T00:00:00Z',valid_from='2027-07-01T00:00:00Z',valid_until='2027-08-01T00:00:00Z',review_status='accepted_synthetic',value_status='declared_synthetic',superseded_by_sha256=None,basis_ref='SYNTHETIC-explicit-validity-hypothesis-not-professional-approval'))
    return p


def exit_registry(args):return registry(args[4].payload['context'],required_exit_sources(args))
