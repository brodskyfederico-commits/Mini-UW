"""Exact-rational periodic IRR polynomial reference. No XIRR, root choice or financial defaults."""
from fractions import Fraction as F
from pathlib import Path
from copy import deepcopy
import json
ROOT=Path(__file__).resolve().parents[1]

def trim(p):
    p=list(p)
    while len(p)>1 and p[-1]==0:p.pop()
    return p or [F(0)]

def degree(p):return -1 if trim(p)==[0] else len(trim(p))-1
def evaluate(p,x):
    value=F(0)
    for c in reversed(p):value=value*x+c
    return value
def derivative(p):return trim([i*c for i,c in enumerate(p)][1:])

def divide(p,q):
    p=trim(p);q=trim(q)
    if degree(q)<0:raise ValueError('polynomial division by zero')
    quotient=[F(0)]*max(1,len(p)-len(q)+1)
    while degree(p)>=degree(q) and degree(p)>=0:
        shift=degree(p)-degree(q);factor=p[-1]/q[-1];quotient[shift]+=factor
        for i,c in enumerate(q):p[i+shift]-=factor*c
        p=trim(p)
    return trim(quotient),p

def gcd(p,q):
    p=trim(p);q=trim(q)
    while degree(q)>=0:p,q=q,divide(p,q)[1]
    return [c/p[-1] for c in p] if degree(p)>=0 else [F(0)]

def square_free(p):
    if degree(p)<=0:return trim(p)
    q,rem=divide(p,gcd(p,derivative(p)))
    assert rem==[0]
    return q

def sturm(p):
    p=square_free(p)
    if degree(p)<=0:return [p]
    seq=[p,derivative(p)]
    while degree(seq[-1])>0:
        rem=divide(seq[-2],seq[-1])[1]
        if degree(rem)<0:break
        seq.append([-x for x in rem])
    return seq

def variations(seq,x):
    signs=[]
    for p in seq:
        v=evaluate(p,x)
        if v:signs.append(1 if v>0 else -1)
    return sum(a!=b for a,b in zip(signs,signs[1:]))

def count(seq,a,b):
    # With zero terms omitted, this convention counts distinct roots in (a,b].
    return variations(seq,a)-variations(seq,b)

def multiplicity(p,a,b):
    m=1
    while degree(p)>0:
        p=gcd(p,derivative(p))
        if degree(p)>0:m+=count(sturm(p),a,b)
    return m

def isolate_periodic(flows,rate_interval_width,split_budget):
    if type(flows) not in (list,tuple) or not flows:raise ValueError('explicit nonempty periodic net-flow vector required')
    if any(type(c) not in (int,F) for c in flows):raise ValueError('exact known rational flows required')
    if type(rate_interval_width) not in (int,F) or rate_interval_width<=0:raise ValueError('explicit positive rational rate-interval width required')
    if type(split_budget) is not int or split_budget<0:raise ValueError('explicit nonnegative integer split budget required')
    original=tuple(F(c) for c in flows);p=trim(original)
    base={'reference_only':True,'publication_authorized':False,'decision':'PENDING','rate_domain':'r > -1; equally spaced periods explicitly assumed','annualized':False,'roots':[],'unresolved_intervals':[],'splits':0,'requested_rate_interval_width':str(rate_interval_width)}
    if degree(p)<0:return dict(base,status='indeterminate',root_classification='identically_zero_net_polynomial',distinct_positive_discount_roots=None,excluded_zero_discount_factor_multiplicity=None)
    zero_factors=0
    while len(p)>1 and p[0]==0:p=p[1:];zero_factors+=1
    base['excluded_zero_discount_factor_multiplicity']=zero_factors
    if degree(p)<=0:return dict(base,status='complete_reference',root_classification='no_admissible_root',distinct_positive_discount_roots=0)
    # Cauchy bound: for x >= 1+max|a_i/a_n|, the leading term strictly dominates
    # the sum of lower terms. It supplies a finite mathematical search bound.
    bound=1+max(abs(c/p[-1]) for c in p[:-1]);seq=sturm(p)
    n=count(seq,F(0),bound);base['distinct_positive_discount_roots']=n
    base['discount_factor_search_upper_bound']=str(bound)
    base['root_classification']='no_admissible_root' if n==0 else 'one_distinct_root' if n==1 else 'multiple_distinct_roots'
    stack=[(F(0),bound,n)] if n else []
    while stack:
        a,b,roots=stack.pop()
        if not roots:continue
        exact=roots==1 and evaluate(p,b)==0
        precise=roots==1 and a>0 and 1/a-1/b<=rate_interval_width
        if exact or precise:
            item={'discount_factor_interval':{'lower':str(a),'upper':str(b),'lower_closed':False,'upper_closed':True},'distinct_roots':1,'multiplicity':multiplicity(p,a,b)}
            if exact:item.update(exact_discount_factor=str(b),exact_periodic_rate=str(1/b-1),periodic_rate_interval=None)
            else:item.update(exact_discount_factor=None,exact_periodic_rate=None,periodic_rate_interval={'lower':str(1/b-1),'upper':str(1/a-1),'lower_closed':True,'upper_closed':False})
            base['roots'].append(item);continue
        if base['splits']>=split_budget:
            base['unresolved_intervals'].append({'discount_factor_lower':str(a),'discount_factor_upper':str(b),'lower_closed':False,'upper_closed':True,'distinct_roots':roots})
            continue
        mid=(a+b)/2;left=count(seq,a,mid);right=count(seq,mid,b)
        assert left>=0 and right>=0 and left+right==roots
        base['splits']+=1
        if right:stack.append((mid,b,right))
        if left:stack.append((a,mid,left))
    base['roots'].sort(key=lambda item:F(item['exact_discount_factor']) if item['exact_discount_factor'] is not None else F(item['discount_factor_interval']['upper']))
    assert len(base['roots'])+sum(i['distinct_roots'] for i in base['unresolved_intervals'])==n
    base['status']='incomplete_reference' if base['unresolved_intervals'] else 'complete_reference'
    return base

def multiply(p,q):
    out=[F(0)]*(len(p)+len(q)-1)
    for i,a in enumerate(p):
        for j,b in enumerate(q):out[i+j]+=a*b
    return trim(out)

def main():
    checks=[]
    def ok(name,condition):
        assert condition,name;checks.append(name)
    width=F(1,100000);budget=2000  # Declared synthetic test settings, never financial defaults.
    def run(flows):return isolate_periodic(flows,width,budget)
    def contains(item,q):
        if item['exact_discount_factor'] is not None:return F(item['exact_discount_factor'])==q
        interval=item['discount_factor_interval'];return F(interval['lower'])<q<=F(interval['upper'])
    def expected(name,flows,qs):
        z=run(flows);ok(name+'_root_count',z['status']=='complete_reference' and z['distinct_positive_discount_roots']==len(qs))
        for q,m in qs:
            matched=[item for item in z['roots'] if contains(item,q)]
            ok(name+'_root_'+str(q),len(matched)==1 and matched[0]['multiplicity']==m)
        for item in z['roots']:
            if item['periodic_rate_interval'] is not None:
                interval=item['periodic_rate_interval'];ok(name+'_explicit_rate_width_'+str(item['discount_factor_interval']['upper']),F(interval['upper'])-F(interval['lower'])<=width)
        return z
    examples={}
    examples['one_positive']=expected('one_positive',[-100,110],[(F(10,11),1)])
    examples['negative']=expected('negative',[-2,1],[(F(2),1)])
    examples['two']=expected('two',[-100,230,-132],[(F(5,6),1),(F(10,11),1)])
    examples['double']=expected('double',[-1,2,-1],[(F(1),2)])
    examples['triple']=expected('triple',[-1,3,-3,1],[(F(1),3)])
    expected('complex_no_real',[1,-1,1],[])
    expected('negative_discount_root',[1,1],[])
    expected('all_inflows',[1,2,3],[])
    expected('all_outflows',[-1,-2,-3],[])
    expected('constant_nonzero',[5],[])
    z=expected('initial_zero_delay',[0,-1,1],[(F(1),1)])
    ok('zero_discount_factor_excluded_not_finite_irr',z['excluded_zero_discount_factor_multiplicity']==1)
    expected('trailing_zero_periods_preserve_roots',[-100,110,0,0],[(F(10,11),1)])
    z=run([0,0,0]);ok('all_zero_is_indeterminate_not_zero_irr',z['status']=='indeterminate' and z['distinct_positive_discount_roots'] is None)
    known=[(F(1,2),1),(F(1),1),(F(2),2),(F(3),1)]
    p=[F(1)]
    for q,m in known:
        for _ in range(m):p=multiply(p,[-q,F(1)])
    p=multiply(p,[F(1),F(1)]);p=multiply(p,[F(1),F(0),F(1)])
    examples['higher_degree']=expected('higher_degree_known_factors',p,known)
    z=run([-2,0,1]);item=z['roots'][0];interval=item['discount_factor_interval']
    ok('irrational_root_is_certified_interval_not_fake_exact_decimal',z['distinct_positive_discount_roots']==1 and item['exact_discount_factor'] is None and F(interval['lower'])**2<2<=F(interval['upper'])**2)
    z=run([4,0,-4,0,1]);item=z['roots'][0];interval=item['discount_factor_interval']
    ok('repeated_irrational_root_multiplicity_retained',z['status']=='complete_reference' and item['multiplicity']==2 and F(interval['lower'])**2<2<=F(interval['upper'])**2)
    expected('closely_spaced_roots',[F(1000001,1000000),-F(2000001,1000000),F(1)],[(F(1),1),(F(1000001,1000000),1)])
    z=isolate_periodic([-100,230,-132],width,0)
    ok('work_budget_exhaustion_is_incomplete',z['status']=='incomplete_reference' and z['roots']==[] and z['unresolved_intervals'][0]['distinct_roots']==2)
    ok('no_first_root_selection',len(examples['two']['roots'])==2 and 'selected_rate' not in examples['two'])
    ok('double_root_found_without_sign_crossing',evaluate([F(-1),F(2),F(-1)],F(1,2))<0 and evaluate([F(-1),F(2),F(-1)],F(3,2))<0 and examples['double']['roots'][0]['multiplicity']==2)
    ok('multiplicity_not_reported_as_two_distinct_rates',examples['double']['distinct_positive_discount_roots']==1)
    for name,z in examples.items():ok(name+'_no_annualization_or_decision',not z['annualized'] and z['decision']=='PENDING' and not z['publication_authorized'])
    old=deepcopy(p);run(p);ok('flows_not_mutated',p==old)
    for name,args in [('missing_flow',([None,1],width,budget)),('floating_flow',([-1,1.1],width,budget)),('boolean_flow',([True,1],width,budget)),('empty_flows',([],width,budget)),('zero_precision',([-1,2],0,budget)),('floating_precision',([-1,2],0.01,budget)),('negative_work_budget',([-1,2],width,-1)),('noninteger_work_budget',([-1,2],width,F(2)))]:
        try:isolate_periodic(*args)
        except ValueError:checks.append(name+'_rejected')
        else:raise AssertionError(name)
    # Sturm endpoint convention: (a,b], including an upper root once and excluding a lower root.
    seq=sturm([F(2),F(-3),F(1)])
    ok('exact_split_endpoint_root_counted_once',count(seq,F(0),F(1))==1 and count(seq,F(1),F(2))==1 and count(seq,F(2),F(3))==0)
    report={'status':'passed','total':len(checks),'checks':checks,'arithmetic':'exact rational polynomial division/gcd/Sturm isolation','synthetic_settings':{'max_periodic_rate_interval_width':str(width),'split_budget':budget,'financial_default':False},'examples':examples,'scope':'Isolated periodic rational-net-flow polynomial root counting/isolation on declared synthetic cases. Not XIRR, calendar-to-return integration, root-selection policy, annualization convention, global price optimization, independent financial audit, real-deal screening or production.'}
    (ROOT/'references/periodic-irr-isolation-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'total':report['total']}))

if __name__=='__main__':main()
