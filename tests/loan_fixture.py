from dataclasses import asdict
import json
from test_foundation import seed


def loan_source(**changes):
    terms={'schema':'miniuw.synthetic-loan-terms.v1','loan_id':'SYNTHETIC-loan-1','regular_intervals_assumed':True,
        'context':asdict(seed()),'principal':{'numerator':'1200','denominator':'1'},'currency':'USD',
        'periodic_rate':{'numerator':'0','denominator':'1'},'amortization_payments':12,
        'maturity_payment':3,'payments_per_year':12,'rate_interval_ref':'SYNTHETIC-payment-interval',
        'annual_equivalent_ref':'SYNTHETIC-annual-equivalent-1','rate_basis':'effective_per_payment_interval',
        'payment_timing':'arrears','fixed_rate':True,'new_draws':False,'capitalized_fees':False,
        'interest_only':False,'rounding':'none_exact','balloon_treatment':'due_after_last_scheduled_payment',
        'origination_date':'2027-06-01','payment_dates':['2027-06-30','2027-07-31','2027-08-31']}
    terms.update(changes)
    return json.dumps(terms).encode()
