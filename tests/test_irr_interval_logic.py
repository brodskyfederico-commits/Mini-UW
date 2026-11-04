from fractions import Fraction as F
from itertools import product
import copy,operator,unittest
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.debt_service import rational
from miniuw_foundation.irr_interval_output import condition_relation,_compare,_annual_enclosure,VALUE_DEFINITION

q=lambda x:rational(F(x))
interval=lambda a,b,lc=True,hc=True:dict(lower=q(a),upper=q(b),lower_closed=lc,upper_closed=hc)
PERIOD='SYNTHETIC-lifecycle:2022-03-01:2027-07-01'
def criterion():
    return dict(metric_id='IRR',definition_ref=VALUE_DEFINITION,unit='fraction',period_ref=PERIOD,
        pass_condition=dict(operator='>=',threshold=q(2)),fail_condition=dict(operator='<=',threshold=q(0)),source_ref='SYNTHETIC-explicit-test')


class IRRIntervalLogicTests(unittest.TestCase):
    def test_exact_partition_oracle_for_operators_closures_and_thresholds(self):
        ops={'>':operator.gt,'>=':operator.ge,'<':operator.lt,'<=':operator.le};checked=0
        for a,b in ((F(-1),F(0)),(F(0),F(1)),(F(-1),F(1))):
            for lc,hc,t,(name,op)in product((False,True),(False,True),map(F,(-2,-1,F(-1,2),0,F(1,2),1,2)),ops.items()):
                # Independent critical-point partition: compare representatives on each side of t.
                points={a,b,t,(a+b)/2,(a+t)/2,(t+b)/2}
                samples=[x for x in points if(a<x<b or x==a and lc or x==b and hc)]
                values={op(x,t)for x in samples};expected='every'if values=={True}else'none'if values=={False}else'mixed'
                self.assertEqual(condition_relation(interval(a,b,lc,hc),q(t),name),expected,(a,b,lc,hc,t,name));checked+=1
        self.assertEqual(checked,336)

    def test_open_and_closed_equality_is_preserved_at_both_endpoints(self):
        self.assertEqual(condition_relation(interval(0,1,False,True),q(0),'>'),'every')
        self.assertEqual(condition_relation(interval(0,1,True,True),q(0),'>'),'mixed')
        self.assertEqual(condition_relation(interval(0,1,True,False),q(1),'<'),'every')
        self.assertEqual(condition_relation(interval(0,1,True,True),q(1),'<'),'mixed')
        self.assertEqual(condition_relation(interval(0,1,True,False),q(1),'>='),'none')
        self.assertEqual(condition_relation(interval(0,1,False,True),q(0),'<='),'none')

    def test_exact_singleton_and_explicit_zero_are_values_not_missing(self):
        for op,expected in (('>=','every'),('<=','every'),('>','none'),('<','none')):
            self.assertEqual(condition_relation(interval(0,0),q(0),op),expected)
        c=criterion();c['pass_condition']['threshold']=q(0);c['fail_condition'].update(operator='<',threshold=q(0))
        state,relations,blockers=_compare(interval(0,0),c,PERIOD)
        self.assertEqual(state,'PASS_CONDITION');self.assertEqual(blockers,[]);self.assertEqual(relations['pass_condition'],'every')

    def test_empty_unknown_inverted_and_nonboolean_enclosures_are_rejected(self):
        samples=[interval(2,1),interval(1,1,False,True),interval(1,1,True,False),dict(interval(0,1),lower=None),
            dict(interval(0,1),lower_closed=1),dict(interval(0,1),upper_closed='true'),dict(interval(0,1),extra=0)]
        for value in samples:
            with self.assertRaises(ValidationError):condition_relation(value,q(0),'>=')
        for threshold,op in ((None,'>='),(q(0),'='),(1.5,'>='),(True,'>=')):
            with self.assertRaises(ValidationError):condition_relation(interval(0,1),threshold,op)

    def test_global_rule_overlap_conflicts_even_outside_observed_interval(self):
        c=criterion();c['pass_condition']['threshold']=q(0);c['fail_condition']['threshold']=q(1)
        state,relations,blockers=_compare(interval(20,30),c,PERIOD)
        self.assertEqual(state,'CONFLICT');self.assertEqual(relations,{})
        self.assertIn('pass_fail_regions_overlap',blockers)
        c['fail_condition'].update(operator='>',threshold=q(10))
        self.assertEqual(_compare(interval(-30,-20),c,PERIOD)[0],'CONFLICT')

    def test_band_retains_pending_reason_and_does_not_become_fail(self):
        c=criterion();before=copy.deepcopy(c)
        state,relations,blockers=_compare(interval(F(1,2),F(3,2)),c,PERIOD)
        self.assertEqual(state,'BAND');self.assertEqual(set(relations.values()),{'none'})
        self.assertEqual(blockers,['intermediate_band_pending_professional_review']);self.assertEqual(c,before)

    def test_each_missing_or_incompatible_criterion_field_blocks_comparison(self):
        for key,value in (('definition_ref',None),('definition_ref','OTHER'),('unit',None),('unit','percent'),
            ('period_ref',None),('period_ref','OTHER'),('source_ref',None)):
            c=criterion();c[key]=value
            state,relations,blockers=_compare(interval(3,4),c,PERIOD)
            self.assertEqual(state,'PENDING');self.assertEqual(relations,{});self.assertTrue(blockers)
        for name in ('pass_condition','fail_condition'):
            for key in ('operator','threshold'):
                c=criterion();c[name][key]=None
                self.assertEqual(_compare(interval(3,4),c,PERIOD)[0],'PENDING')
        self.assertEqual(_compare(None,criterion(),PERIOD)[0],'PENDING')

    def test_crossing_threshold_stays_pending_without_midpoint_rounding_or_precision_change(self):
        c=criterion();c['pass_condition']['threshold']=q(F(3,2));before=copy.deepcopy(c)
        state,relations,blockers=_compare(interval(1,2),c,PERIOD)
        self.assertEqual(state,'PENDING');self.assertEqual(relations['pass_condition'],'mixed')
        self.assertIn('IRR_enclosure_crosses_criterion_boundary',blockers);self.assertEqual(c,before)
        # A tiny enclosure straddling zero must not be rounded into a definite result.
        c['pass_condition']['threshold']=q(0);c['fail_condition']['threshold']=q(-1)
        self.assertEqual(_compare(interval(F(-1,10**20),F(1,10**20)),c,PERIOD)[0],'PENDING')

    def test_missing_incomplete_multiple_or_unannualized_roots_never_pick_a_root(self):
        ev=dict(annualization_blockers=[])
        self.assertIsNone(_annual_enclosure(None,ev)[0])
        for result in (dict(status='incomplete_synthetic',distinct_positive_discount_roots=1,roots=[{}]),
            dict(status='complete_synthetic',distinct_positive_discount_roots=2,roots=[{},{}]),
            dict(status='complete_synthetic',distinct_positive_discount_roots=0,roots=[])):
            story=dict(periodic_irr=result,annual_irr_roots=[])
            self.assertIsNone(_annual_enclosure(story,ev)[0])
        story=dict(periodic_irr=dict(status='complete_synthetic',distinct_positive_discount_roots=1,roots=[{}]),annual_irr_roots=[])
        self.assertIsNone(_annual_enclosure(story,ev)[0])

    def test_exact_root_enclosure_is_closed_without_creating_selected_rate(self):
        story=dict(periodic_irr=dict(status='complete_synthetic',distinct_positive_discount_roots=1,roots=[{}]),
            annual_irr_roots=[dict(exact_annual_rate=q(F(1,10)),annual_rate_interval=None)],selected_IRR=None)
        enclosure,blockers=_annual_enclosure(story,dict(annualization_blockers=[]))
        self.assertEqual(enclosure,interval(F(1,10),F(1,10)));self.assertEqual(blockers,[]);self.assertIsNone(story['selected_IRR'])

    def test_supplied_inverse_directions_are_respected_without_more_is_better_default(self):
        c=criterion();c['pass_condition'].update(operator='<=',threshold=q(0));c['fail_condition'].update(operator='>=',threshold=q(2))
        self.assertEqual(_compare(interval(-2,-1),c,PERIOD)[0],'PASS_CONDITION')
        self.assertEqual(_compare(interval(3,4),c,PERIOD)[0],'FAIL_CONDITION')
        self.assertEqual(_compare(interval(F(1,2),F(3,2)),c,PERIOD)[0],'BAND')


if __name__=='__main__':unittest.main()
