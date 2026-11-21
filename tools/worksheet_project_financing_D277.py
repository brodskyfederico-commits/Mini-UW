"""Opt-in synthetic bank addendum for explicitly eligible M3 project uses.

v37 remains direct-hard only. v38 requires source bytes, quote/workbook bindings,
all eligible role values and a separate declared invoice share. Neither a target
TDC ratio nor a permanent-loan amount can resize construction debt at runtime.
"""
from hashlib import sha256
import json
from fractions import Fraction as Q
from worksheet_frontiers_D275 import fraction as F,rational as R,digest

SCHEMA='miniuw.synthetic-native-rental-inputs.v38'
PROFILE='miniuw.synthetic-native-monthly-project-financing.v1'
POLICY='SYNTHETIC-D277-declared-project-construction-financing'
BASIS='documented_M3_roles_excluding_financing_tax_reserves_and_leaseup'
ROLES=('land','direct_hard','contingency','soft','ti_lc')
ADDENDUM='miniuw.synthetic-bank-eligible-project-costs.v1'


def require(ok,reason):
 if not ok:raise ValueError(reason)


def eligible_costs(cfg,documents,*,scenario,quote_sha256,workbook_sha256,development,budget,ltc,invoice_share):
 ref=cfg.get('project_eligibility');require(isinstance(ref,dict) and ref.get('locator') and isinstance(ref.get('sha256'),str),'Falta addendum de costos elegibles con cita')
 raw=documents.get(ref['sha256']);require(isinstance(raw,bytes) and sha256(raw).hexdigest()==ref['sha256'],'Addendum de costos elegibles ausente o alterado');doc=json.loads(raw)
 expected=dict(land=R(F(development['evaluated_purchase_price'])+F(development['land_closing_cost'])),direct_hard=budget['direct_hard_cost'],contingency=budget['contingency_reserve'],soft=budget['soft_budget'],ti_lc=budget['ti_lc_cost'])
 require(doc.get('schema')==ADDENDUM and doc.get('usage')=='synthetic_test_only' and doc.get('supersedes')==['eligible_cost'] and doc.get('scenario')==scenario and doc.get('currency')=='USD' and doc.get('bank_quote_sha256')==quote_sha256 and doc.get('workbook_sha256')==workbook_sha256 and doc.get('eligible_cost_basis')==BASIS,'Addendum de otro ámbito, cotización o revisión')
 require(doc.get('eligible_roles')==list(ROLES) and set(doc.get('role_amounts',{}))==set(ROLES),'Inventario de partidas elegibles incompleto; no se supone cero')
 for role in ROLES:require(F(doc['role_amounts'][role])==F(expected[role]) and F(expected[role])>=0,'Partida elegible no concilia con M3: '+role)
 require(F(doc.get('ltc_cap'))==F(ltc) and F(doc.get('requested_invoice_share'))==F(invoice_share) and 0<=F(invoice_share)<=F(ltc)<=1,'LTC o porcentaje de draw no coincide con el respaldo')
 total=sum((F(v) for v in expected.values()),Q());require(total>0 and F(doc.get('eligible_total'))==total,'Costo elegible total no conciliado')
 return dict(total=R(total),basis=BASIS,roles=expected,source=ref,document_sha256=ref['sha256'],definition='Eligible M3 uses exclude construction financing, property tax, insurance premium, residential lease-up and operating reserves. Draw/TDC is reported separately, never equated with C51.')


def project_draws(periods,eligibility,share,available):
 totals={role:Q() for role in ROLES};additions=[]
 for index,period in enumerate(periods):
  for e in period['events']:
   require(e['kind']=='use','v38 debe construir draws desde facturas M3, no aceptar otros draws precargados')
   identifier=e['id'];role='land' if identifier=='land-and-closing' else 'direct_hard' if identifier.startswith('hard-invoice-') else 'soft' if identifier.startswith('soft-') else 'contingency' if identifier=='contingency' else 'ti_lc' if identifier.startswith('TI-LC-') else None
   if role is None:require(identifier=='residential-leaseup-prefund','Uso M3 no clasificado para elegibilidad');continue
   value=F(e['amount']);totals[role]+=value;additions.append((index,dict(id='project-draw-'+identifier,kind='draw',date=e['date'],amount=R(value*F(share)),eligible_invoice=R(value),available_new_draw=available,invoice_id='SYNTHETIC-D277-INVOICE-'+identifier,source_ref='sha256:'+eligibility['document_sha256'],source_use_id=identifier,eligible_role=role)))
 require(all(totals[k]==F(eligibility['roles'][k]) for k in ROLES),'Facturas elegibles no concilian con el presupuesto por partida')
 for index,event in additions:periods[index]['events'].append(event)
 return periods
