from miniuw_foundation.sale_costs import produce_sale_costs
from miniuw_foundation.bounded_sale_costs import produce_bounded_sale_costs
from sale_cost_test_support import evidence,valuation,cost_source,bridge_spec,raw,sha


def bounds_spec(cost_raw,cost_run):
    p=cost_run.payload;rules=[]
    for item in p['cost_rows']:
        row=item['claim']
        if row['applicability']!='included':continue
        def bound(enabled,value,label):
            return dict(enabled=enabled,value=None if value is None else dict(numerator=str(value),denominator='1'),currency=p['currency'],as_of_date=p['sale_date'],source_ref='SYNTHETIC-explicit-'+row['cost_id']+'-'+label)
        fee=row['cost_id']=='fee'
        rules.append(dict(cost_id=row['cost_id'],rule_basis_ref='SYNTHETIC-per-item-money-clamp-not-contract-authentication',minimum=bound(fee,25 if fee else None,'minimum'),maximum=bound(fee,40 if fee else None,'maximum')))
    return dict(schema='miniuw.synthetic-per-item-sale-cost-bounds.v1',profile='SYNTHETIC-PER-ITEM-CLAMP-TO-EXPLICIT-MONEY-LIMITS-v1',cost_source_sha256=sha(cost_raw),cost_run_sha256=cost_run.sha256,rule_inventory_declared_complete=True,rule_inventory_basis_ref='SYNTHETIC-all-included-items-have-explicit-limit-status',rules=rules)


def case(compatible=True):
    e=evidence(compatible);nr,n,vr,v=valuation();cr=raw(cost_source(v));c=produce_sale_costs(cr)
    br=raw(bounds_spec(cr,c));bounded=produce_bounded_sale_costs(cr,c,br)
    spec=bridge_spec(e,vr,v,cr,c)
    spec.update(schema='miniuw.synthetic-bounded-exit-sale.v1',revision_id='SYNTHETIC-bounded-sale',bounds_source_sha256=sha(br),bounded_run_sha256=bounded.sha256)
    return(e,nr,n,vr,v,cr,c,br,bounded,raw(spec))
