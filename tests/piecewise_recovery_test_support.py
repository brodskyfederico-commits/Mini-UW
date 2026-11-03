import json
from fractions import Fraction
from miniuw_foundation.debt_service import rational
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.exit_value import produce_exit_value
from miniuw_foundation.sale_costs import produce_sale_costs
from miniuw_foundation.bounded_sale_costs import produce_bounded_sale_costs
from miniuw_foundation.bounded_exit_sale import assemble_bounded_exit_sale
from project_test_support import load_case
from sale_revision_test_support import make_evidence
from sale_cost_test_support import valuation,cost_source,bridge_spec,raw,sha
from bounded_cost_test_support import bounds_spec


def build_case(rate=Fraction(1,20),minimum=25,maximum=40,extra_cash=0,extra_uses=0,compatible=True,retain_valuation=False,noi_zero=False):
    project=load_case()
    if not retain_valuation:project['closings'][1]['valuation_claim']=None
    project['closings'][1]['amounts']['other_cash_sources']['value']=rational(Fraction(extra_cash))
    project['closings'][1]['amounts']['other_cash_uses']['value']=rational(Fraction(extra_uses))
    e=make_evidence(compatible=compatible,project=project);nr,n,vr,v=valuation()
    if noi_zero:
        p=json.loads(nr);p['income_rows'][0]['value']=rational(Fraction(0));nr=raw(p);n=produce_operating_noi(nr)
        p=json.loads(vr);p.update(noi_source_sha256=sha(nr),noi_run_sha256=n.sha256);vr=raw(p);v=produce_exit_value(nr,n,vr)
    if retain_valuation:
        p=json.loads(vr);p['cap_rate']['value']=rational(Fraction(2,25));vr=raw(p);v=produce_exit_value(nr,n,vr)
    source=cost_source(v);source['costs'][1]['value']=rational(Fraction(rate));cr=raw(source);c=produce_sale_costs(cr)
    spec=bounds_spec(cr,c);rule=next(r for r in spec['rules']if r['cost_id']=='fee')
    for key,value in [('minimum',minimum),('maximum',maximum)]:rule[key].update(enabled=value is not None,value=None if value is None else rational(Fraction(value)))
    br=raw(spec);b=produce_bounded_sale_costs(cr,c,br);s=bridge_spec(e,vr,v,cr,c)
    s.update(schema='miniuw.synthetic-bounded-exit-sale.v1',bounds_source_sha256=sha(br),bounded_run_sha256=b.sha256)
    args=(e,nr,n,vr,v,cr,c,br,b,raw(s));base=assemble_bounded_exit_sale(*args)
    return args,base


def recovery_spec(base,lower=0,upper=2000,budget=129):
    return dict(schema='miniuw.synthetic-piecewise-bounded-sale-recovery.v1',base_bounded_run_sha256=base.sha256,
        gross_price_domain=dict(lower=rational(Fraction(lower)),upper=rational(Fraction(upper))),
        cost_profile_domain_basis_ref='SYNTHETIC-per-item-clamp-profile-assumed-only-in-explicit-domain',
        other_sources_fixed_basis_ref='SYNTHETIC-all-other-cash-debt-dates-frozen-not-market-scenario',segment_budget=budget)
