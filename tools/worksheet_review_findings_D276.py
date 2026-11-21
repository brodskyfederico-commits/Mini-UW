"""Group substantiated common-cause findings without removing any criterion.

Grouping changes the review narrative only. The metric comparison list, cash,
RLV intersection, simulated decision and adoption state remain untouched.
"""
from copy import deepcopy
from hashlib import sha256
import json
from worksheet_frontiers_D275 import digest
from miniuw_foundation.lorena_screening import BASES

SCHEMA='miniuw.synthetic-common-cause-findings.v1'
STATES={'PASS_SIMULATED','FAIL_SIMULATED','PENDING','N/A'}


def findings(comparisons,causes,documents,criteria_revision):
 try:
  if not isinstance(comparisons,list) or not isinstance(causes,list) or not isinstance(documents,dict):raise ValueError('Falta inventario de comparaciones o causas; no se cuenta como cero')
  expected={(s,m) for s in ('Base','Downside') for m in BASES};indexed={}
  for row in comparisons:
   key=(row.get('scenario'),row.get('metric_id'))
   if key not in expected or key in indexed or row.get('state') not in STATES:raise ValueError('Comparación ausente, duplicada o no reconocida')
   indexed[key]=row
  if set(indexed)!=expected:raise ValueError('Falta alguna comparación aplicable; no se omite del recuento')
  groups=[];claimed=set();rejected=[]
  for cause in causes:
   if not isinstance(cause,dict):raise ValueError('Causa inválida')
   scenario=cause.get('scenario');keys={(scenario,m) for m in ('YoC','spread')};ref=cause.get('source');reason=None
   if not isinstance(ref,dict) or not isinstance(ref.get('sha256'),str) or not isinstance(ref.get('locator'),str) or not ref['locator'].strip():reason='Falta evidencia de causa compartida'
   else:
    raw=documents.get(ref['sha256'])
    if not isinstance(raw,bytes) or sha256(raw).hexdigest()!=ref['sha256']:reason='Fuente causal ausente o alterada'
    else:
     source=json.loads(raw)
     if source!=cause.get('declaration') or source.get('schema')!=SCHEMA or source.get('scenario')!=scenario or source.get('criteria_revision')!=criteria_revision or not isinstance(criteria_revision,str) or not criteria_revision.startswith('SYNTHETIC-') or source.get('metric_ids')!=['YoC','spread'] or source.get('common_cause_proved') is not True or not source.get('cause_id') or not source.get('source_ref','').startswith('SYNTHETIC-'):reason='Definición de causalidad, revisión o ámbito no confirmado'
     elif source.get('comparison_sha256')!=digest([indexed.get((scenario,m)) for m in ('YoC','spread')]):reason='La causa no corresponde a estas comparaciones vigentes'
   if keys & claimed:raise ValueError('Una métrica no puede contarse en dos grupos')
   if reason is None and not all(indexed.get(k,{}).get('state')=='FAIL_SIMULATED' for k in keys):reason='Ambas métricas deben tener incumplimiento verificado'
   if reason:rejected.append(dict(scenario=scenario,state='PENDING',reason=reason));continue
   claimed|=keys;groups.append(dict(scenario=scenario,kind='COMMON_CAUSE',metric_ids=['YoC','spread'],cause_id=source['cause_id'],source=deepcopy(ref),label='Un hallazgo causal; se conservan ambos criterios incumplidos'))
  for key,row in indexed.items():
   if row['state']=='FAIL_SIMULATED' and key not in claimed:groups.append(dict(scenario=key[0],kind='INDIVIDUAL',metric_ids=[key[1]],label='Incumplimiento verificado por métrica'))
  counts={s:dict(failing_metrics=sum(k[0]==s and r['state']=='FAIL_SIMULATED' for k,r in indexed.items()),review_findings=sum(g['scenario']==s for g in groups),pending_metrics=sum(k[0]==s and r['state']=='PENDING' for k,r in indexed.items())) for s in ('Base','Downside')}
  return dict(schema=SCHEMA,state='GROUPED_SYNTHETIC',findings=groups,counts=counts,unproved_causes=rejected,comparisons=deepcopy(comparisons),comparisons_sha256=digest(comparisons),all_applicable_criteria_preserved=True,decision='PENDING',criteria_adopted=False)
 except (ValueError,KeyError,TypeError,AttributeError) as err:return dict(schema=SCHEMA,state='PENDING',reason=str(err),findings=None,counts=None,all_applicable_criteria_preserved=True,decision='PENDING',criteria_adopted=False)
