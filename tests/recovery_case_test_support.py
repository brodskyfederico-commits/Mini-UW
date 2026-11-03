import json
from fractions import Fraction
from miniuw_foundation.debt_service import rational
from miniuw_foundation.exit_value import produce_exit_value
from miniuw_foundation.sale_costs import produce_sale_costs
from miniuw_foundation.bounded_sale_costs import produce_bounded_sale_costs
from miniuw_foundation.bounded_exit_sale import assemble_bounded_exit_sale
from piecewise_recovery_test_support import raw,sha


def reprice(arguments,price,fee=None):
    args=list(arguments);spec=json.loads(args[3]);spec['cap_rate']['value']=rational(Fraction(40)/Fraction(price))
    spec['cap_rate']['source_ref']='SYNTHETIC-explicit-case-price-not-investment-target'
    args[3]=raw(spec);args[4]=produce_exit_value(args[1],args[2],args[3])
    source=json.loads(args[5]);source['gross_price'].update(value=args[4].payload['candidate_value'],source_ref='miniuw:synthetic-exit-value:'+args[4].sha256+'#/candidate_value')
    if fee is not None:source['costs'][1]['value']=rational(Fraction(fee))
    args[5]=raw(source);args[6]=produce_sale_costs(args[5]);bounds=json.loads(args[7])
    bounds.update(cost_source_sha256=sha(args[5]),cost_run_sha256=args[6].sha256)
    args[7]=raw(bounds);args[8]=produce_bounded_sale_costs(args[5],args[6],args[7]);spec=json.loads(args[9])
    spec.update(exit_spec_sha256=sha(args[3]),exit_run_sha256=args[4].sha256,cost_source_sha256=sha(args[5]),cost_run_sha256=args[6].sha256,bounds_source_sha256=sha(args[7]),bounded_run_sha256=args[8].sha256,revision_id='SYNTHETIC-explicit-case-'+str(price))
    args[9]=raw(spec);result=tuple(args)
    return result,assemble_bounded_exit_sale(*result)
