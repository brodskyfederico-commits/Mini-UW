"""T100 exact periodic IRR with positive primitive-content normalization.

Versioned successor to T24; no mutation of its globals, source or archived results.
"""
from fractions import Fraction as F
from contextvars import ContextVar
from pathlib import Path
import hashlib
from math import gcd as integer_gcd,lcm
from .drafts import ValidationError

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
_COUNTER=ContextVar('miniuw_primitive_irr_budget')
METHOD='positive_primitive_content_gcd_sturm_v1'
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T100.md'
class RootBudgetExceeded(ValidationError):pass

def checked(value):
    counter=_COUNTER.get();counter['used']+=1
    if counter['used']>counter['limit']or value.numerator.bit_length()>4096 or value.denominator.bit_length()>4096:raise RootBudgetExceeded('root arithmetic budget exceeded')
    return value

def add(a,b):return checked(F(a)+b)
def sub(a,b):return checked(F(a)-b)
def mul(a,b):return checked(F(a)*b)
def div(a,b):return checked(F(a)/b)

def trim(p):
    p=list(p)
    while len(p)>1 and p[-1]==0:p.pop()
    return p or [F(0)]

def degree(p):return -1 if trim(p)==[0] else len(trim(p))-1
def evaluate(p,x):
    value=F(0)
    for c in reversed(p):value=add(mul(value,x),c)
    return value
def derivative(p):return trim([mul(i,c) for i,c in enumerate(p)][1:])

def divide(p,q):
    p=trim(p);q=trim(q)
    if degree(q)<0:raise ValueError('polynomial division by zero')
    quotient=[F(0)]*max(1,len(p)-len(q)+1)
    while degree(p)>=degree(q) and degree(p)>=0:
        shift=degree(p)-degree(q);factor=div(p[-1],q[-1]);quotient[shift]=add(quotient[shift],factor)
        for i,c in enumerate(q):p[i+shift]=sub(p[i+shift],mul(factor,c))
        p=trim(p)
    return trim(quotient),p

def primitive(p):
    p=[F(c)for c in trim(p)];den=1
    for c in p:den=int(checked(F(lcm(den,c.denominator))))
    integers=[int(checked(F(c.numerator*(den//c.denominator))))for c in p]
    content=0
    for n in integers:
        content=integer_gcd(content,abs(n))
        checked(F(content))
    if content==0:return [F(0)]
    # The divisor is positive: preserve every coefficient's sign and all zeros.
    return [checked(F(n//content))for n in integers]

def gcd(p,q):
    p,q=primitive(p),primitive(q)
    while degree(q)>=0:p,q=q,primitive(divide(p,q)[1])
    return [div(c,p[-1])for c in p]if degree(p)>=0 else[F(0)]

def square_free(p):
    if degree(p)<=0:return trim(p)
    q,rem=divide(p,gcd(p,derivative(p)))
    assert rem==[0]
    return q

def sturm(p):
    p=primitive(square_free(p))
    if degree(p)<=0:return [p]
    seq=[p,primitive(derivative(p))]
    while degree(seq[-1])>0:
        rem=divide(seq[-2],seq[-1])[1]
        if degree(rem)<0:break
        seq.append(primitive([-x for x in rem]))
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

def _isolate(flows,rate_interval_width,split_budget):
    if type(flows) not in (list,tuple) or not flows:raise ValueError('explicit nonempty periodic net-flow vector required')
    if any(type(c) not in (int,F) for c in flows):raise ValueError('exact known rational flows required')
    if type(rate_interval_width) not in (int,F) or rate_interval_width<=0:raise ValueError('explicit positive rational rate-interval width required')
    if type(split_budget) is not int or split_budget<0:raise ValueError('explicit nonnegative integer split budget required')
    original=tuple(F(c) for c in flows);p=trim(original)
    base={'synthetic_profile_only':True,'publication_authorized':False,'decision':'PENDING','rate_domain':'r > -1; equally spaced periods explicitly assumed','annualized':False,'roots':[],'unresolved_intervals':[],'splits':0,'requested_rate_interval_width':str(rate_interval_width)}
    if degree(p)<0:return dict(base,status='indeterminate',root_classification='identically_zero_net_polynomial',distinct_positive_discount_roots=None,excluded_zero_discount_factor_multiplicity=None)
    zero_factors=0
    while len(p)>1 and p[0]==0:p=p[1:];zero_factors+=1
    base['excluded_zero_discount_factor_multiplicity']=zero_factors
    if degree(p)<=0:return dict(base,status='complete_synthetic',root_classification='no_admissible_root',distinct_positive_discount_roots=0)
    # Cauchy bound: for x >= 1+max|a_i/a_n|, the leading term strictly dominates
    # the sum of lower terms. It supplies a finite mathematical search bound.
    bound=add(1,max(abs(div(c,p[-1])) for c in p[:-1]));seq=sturm(p)
    n=count(seq,F(0),bound);base['distinct_positive_discount_roots']=n
    base['discount_factor_search_upper_bound']=str(bound)
    base['root_classification']='no_admissible_root' if n==0 else 'one_distinct_root' if n==1 else 'multiple_distinct_roots'
    stack=[(F(0),bound,n)] if n else []
    while stack:
        a,b,roots=stack.pop()
        if not roots:continue
        exact=roots==1 and evaluate(p,b)==0
        precise=roots==1 and a>0 and sub(div(1,a),div(1,b))<=rate_interval_width
        if exact or precise:
            item={'discount_factor_interval':{'lower':str(a),'upper':str(b),'lower_closed':False,'upper_closed':True},'distinct_roots':1,'multiplicity':multiplicity(p,a,b)}
            if exact:item.update(exact_discount_factor=str(b),exact_periodic_rate=str(sub(div(1,b),1)),periodic_rate_interval=None)
            else:item.update(exact_discount_factor=None,exact_periodic_rate=None,periodic_rate_interval={'lower':str(sub(div(1,b),1)),'upper':str(sub(div(1,a),1)),'lower_closed':True,'upper_closed':False})
            base['roots'].append(item);continue
        if base['splits']>=split_budget:
            base['unresolved_intervals'].append({'discount_factor_lower':str(a),'discount_factor_upper':str(b),'lower_closed':False,'upper_closed':True,'distinct_roots':roots})
            continue
        mid=div(add(a,b),2);left=count(seq,a,mid);right=count(seq,mid,b)
        assert left>=0 and right>=0 and left+right==roots
        base['splits']+=1
        if right:stack.append((mid,b,right))
        if left:stack.append((a,mid,left))
    base['roots'].sort(key=lambda item:F(item['exact_discount_factor']) if item['exact_discount_factor'] is not None else F(item['discount_factor_interval']['upper']))
    assert len(base['roots'])+sum(i['distinct_roots'] for i in base['unresolved_intervals'])==n
    base['status']='incomplete_synthetic' if base['unresolved_intervals'] else 'complete_synthetic'
    return base


def isolate_primitive_periodic_returns(flows,rate_interval_width,split_budget,operation_budget):
    if type(flows)not in(list,tuple)or not flows or len(flows)>65:raise ValidationError('one to 65 explicit regular-period flows required')
    if any(type(x)not in(int,F)for x in flows):raise ValidationError('exact flows required')
    if type(rate_interval_width)not in(int,F)or rate_interval_width<=0:raise ValidationError('explicit positive rate interval width required')
    if type(split_budget)is not int or not 0<=split_budget<=2048:raise ValidationError('explicit bounded split budget required')
    if type(operation_budget)is not int or not 1<=operation_budget<=200000:raise ValidationError('explicit bounded arithmetic budget required')
    counter={'used':0,'limit':operation_budget};token=_COUNTER.set(counter)
    try:
        checked(F(rate_interval_width))
        for value in flows:checked(F(value))
        result=_isolate(flows,F(rate_interval_width),split_budget)
    except RootBudgetExceeded:
        result={'status':'incomplete_synthetic','root_classification':'arithmetic_budget_exhausted','roots':[],
            'distinct_positive_discount_roots':None,'unresolved_intervals':[],'annualized':False,
            'decision':'PENDING','publication_authorized':False,'synthetic_profile_only':True}
    finally:_COUNTER.reset(token)
    result.update(component='T100',method=METHOD,definition_sha256=hashlib.sha256(DEFINITION.read_bytes()).hexdigest(),coefficient_bit_limit=4096,engine_sha256=ENGINE_SHA256,arithmetic_operations=counter['used'],operation_budget=operation_budget,selected_rate=None)
    return result
