"""Independent review instruments, never substitutes for real authorization."""
from datetime import date
from hashlib import sha256
from math import ceil,sqrt
from statistics import NormalDist
from worksheet_frontiers_D275 import fraction

ROLE_SCHEMA='miniuw.roles-registry.v1'
ROLES=('official_evidence_custodian','criteria_owner','financial_reviewer','authorized_approver')
ROLE_FIELDS=('name','actor_id','scope','designated_on','valid_from','valid_until','appointment_sha256')
STUDY_SCHEMA='miniuw.false-green-study.v1'
DOCUMENT_TYPES=('plano','cotizacion_gc','term_sheet','fiscal')


def empty_roles():return dict(schema=ROLE_SCHEMA,roles={r:{k:None for k in ROLE_FIELDS} for r in ROLES})

def review_roles(registry,as_of,documents):
 """Check nominations against supplied bytes; do not authenticate signatures.

 Structural completeness is not identity verification, approval, deployment or
 permission to make a real decision. The existing authenticated human gate is
 still required even for a completely populated registry.
 """
 if not isinstance(registry,dict) or registry.get('schema')!=ROLE_SCHEMA or set(registry.get('roles',{}))!=set(ROLES):
  raise ValueError('Registro de los cuatro roles ausente o incompatible')
 today=date.fromisoformat(as_of);result={}
 for role,record in registry['roles'].items():
  issues=[]
  if not isinstance(record,dict) or set(record)!=set(ROLE_FIELDS):issues.append('Falta el contrato completo del rol')
  else:
   for key in ROLE_FIELDS:
    value=record[key]
    if not isinstance(value,str) or not value.strip():issues.append('Campo por completar: '+key)
   try:
    start,end,appointed=(date.fromisoformat(record[k]) for k in ('valid_from','valid_until','designated_on'))
    if not appointed<=start<=today<=end:issues.append('Designación o vigencia incompatible con la fecha de corte')
   except (TypeError,ValueError):issues.append('Faltan fechas válidas de designación y vigencia')
   h=record['appointment_sha256'];raw=documents.get(h) if isinstance(h,str) else None
   if not isinstance(raw,bytes) or sha256(raw).hexdigest()!=h:issues.append('Falta documento de designación con huella coincidente')
  result[role]=dict(state='PENDING' if issues else 'STRUCTURALLY_COMPLETE',
   label='responsable por designar' if not isinstance(record,dict) or not record.get('name') else record['name'],
   issues=issues,identity_authenticated=False,approval_authenticated=False)
 return dict(schema=ROLE_SCHEMA,roles=result,structurally_complete=all(not r['issues'] for r in result.values()),
  real_decision='PENDING',formal_gate='PENDING · se requiere identidad y autoridad acreditadas por el carril humano',deployment_enabled=False)


def wilson(successes,n,confidence):
 if type(successes) is not int or type(n) is not int or not 0<=successes<=n or not 0<float(confidence)<1:
  raise ValueError('Muestra, conteo o confianza inválidos')
 if n==0:return dict(state='PENDING',lower=None,upper=None,reason='No hay observaciones completas')
 z=NormalDist().inv_cdf((1+float(confidence))/2);p=successes/n;z2=z*z
 center=(p+z2/(2*n))/(1+z2/n);radius=z*sqrt(p*(1-p)/n+z2/(4*n*n))/(1+z2/n)
 return dict(state='CALCULATED',lower=max(0.,center-radius),upper=min(1.,center+radius),method='Wilson bilateral',confidence=float(confidence))

def zero_event_sample_size(maximum_rate,confidence):
 p=float(fraction(maximum_rate));cf=float(fraction(confidence))
 if not 0<p<1 or not 0<cf<1:raise ValueError('Tasa máxima y confianza deben declararse entre cero y uno')
 z=NormalDist().inv_cdf((1+cf)/2)
 n=max(1,ceil(z*z*(1-p)/p))
 # Protect the boundary against floating-point rounding of a confidence limit.
 while wilson(0,n,cf)['upper']>p:n+=1
 return n


def false_green_study(spec,documents):
 """Count a green without valid evidence as false, even when its value agrees.

 Missing independent human labels are reported and never counted as verified
 negatives. No rate is certified for the complete sample until every label is
 resolved. The study does not turn a human's unverified identity into approval.
 """
 if not isinstance(spec,dict) or spec.get('schema')!=STUDY_SCHEMA or spec.get('population') not in ('synthetic_test','real_documents'):
  raise ValueError('Falta declarar la muestra y su carácter sintético o real')
 confidence=fraction(spec.get('confidence'));maximum=fraction(spec.get('maximum_rate'))
 if confidence!=fraction('0.95'):raise ValueError('Este protocolo requiere confianza bilateral explícita de 95 %')
 rows=spec.get('critical_fields');expected=spec.get('expected_ids')
 if not isinstance(rows,list) or not rows or not isinstance(expected,list) or not expected or len(set(expected))!=len(expected):
  raise ValueError('Falta el inventario explícito de datos críticos')
 ids=[row.get('id') for row in rows if isinstance(row,dict)]
 if len(ids)!=len(rows) or len(set(ids))!=len(ids) or set(ids)!=set(expected):raise ValueError('Muestra incompleta o datos críticos duplicados')
 def evidence(record):
  if not isinstance(record,dict) or not isinstance(record.get('locator'),str) or not record['locator'].strip():return False
  h=record.get('sha256');raw=documents.get(h) if isinstance(h,str) else None
  return isinstance(raw,bytes) and sha256(raw).hexdigest()==h
 reviewed=[]
 for row in rows:
  if row.get('document_type') not in DOCUMENT_TYPES or not isinstance(row.get('bot'),str) or row['bot'] not in {f'B{i:02}' for i in range(1,18)}:
   raise ValueError('Tipo documental o bot fuera del inventario')
  human=row.get('independent_human_reference');claim=row.get('bot_claim')
  if not isinstance(claim,dict) or claim.get('state') not in ('GREEN','PENDING'):raise ValueError('Falta la observación explícita del bot')
  issue=None;fg=False
  if not isinstance(human,dict) or not isinstance(human.get('reviewer_id'),str) or not human['reviewer_id'].strip() or not evidence(human.get('evidence')):
   issue='Falta referencia humana independiente con fuente'
  elif not isinstance(human.get('supported'),bool):issue='Falta resolución humana del respaldo'
  elif claim['state']=='GREEN':
   # Unit, scenario and definition agreement are required in addition to value.
   compatible=all(claim.get(k) is not None and claim.get(k)==human.get(k) for k in ('unit','basis','scenario'))
   try:agree=fraction(claim.get('value'))==fraction(human.get('value'))
   except (ValueError,TypeError,ZeroDivisionError):agree=False
   expected=human.get('evidence');claimed=claim.get('evidence')
   citation_matches=isinstance(claimed,dict) and all(claimed.get(k)==expected.get(k) for k in ('sha256','locator'))
   fg=not human['supported'] or not evidence(claimed) or not citation_matches or not compatible or not agree
  reviewed.append(dict(id=row['id'],green_claim=claim['state']=='GREEN',bot=row['bot'],document_type=row['document_type'],state='PENDING' if issue else 'REVIEWED',
   false_green=None if issue else fg,reason=issue,green_without_citation=claim['state']=='GREEN' and not evidence(claim.get('evidence'))))
 def summary(part):
  complete=[x for x in part if x['state']=='REVIEWED'];n=len(complete);bad=sum(x['false_green'] for x in complete)
  greens=sum(row['green_claim'] for row in part)
  return dict(critical_fields=len(part),reviewed=n,pending=len(part)-n,false_greens=bad,green_claims=greens,abstentions=len(part)-greens,green_coverage=None if not part else greens/len(part),
   rate=None if len(part)!=n or n==0 else bad/n,observed_rate_on_reviewed_only=None if not n else bad/n,
   confidence_interval_on_reviewed_only=wilson(bad,n,float(confidence)),state='PENDING' if len(part)!=n else 'MEASURED',
   zero_false_green_goal_met=None if len(part)!=n else bad==0)
 return dict(schema=STUDY_SCHEMA,population=spec['population'],overall=summary(reviewed),
  by_document_type={k:summary([x for x in reviewed if x['document_type']==k]) for k in sorted({x['document_type'] for x in reviewed})},
  by_bot={k:summary([x for x in reviewed if x['bot']==k]) for k in sorted({x['bot'] for x in reviewed})},
  rows=reviewed,zero_event_sample_size=zero_event_sample_size(maximum,confidence),maximum_rate=str(maximum),
  sample_size_basis='Wilson bilateral 95 %, supuesto de cero falsos verdes; observaciones independientes y muestra representativa requeridas',
  real_empirical_certification=False,real_decision='PENDING',deployment_enabled=False)
