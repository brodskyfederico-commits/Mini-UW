"""Source-backed comparator experiment; historical thresholds never become deal defaults."""
from fractions import Fraction
from pathlib import Path
import hashlib,json,re
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from io import BytesIO
from .drafts import ValidationError,ContextSeed,canonical,nonempty
from .intake import _unique_object,_invalid_constant
from .debt_service import _fraction
from .screening import SCHEMA as SCREEN_SCHEMA,AGGREGATION,simulate_screening

ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SOURCE_SHA256='38b78d40013b9338511d2917de6c4347be1ec812712b4b4b18e7308bb6c28ab9'
SCHEMA='miniuw.synthetic-documented-threshold-rehearsal.v1'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
HEADER=['Metric (unit)','PASS – Base','PASS – Downside','FAIL – Base']
ROWS=[('Yield on Cost, min (%)','YoC'),('Spread over market cap rate, min (bps)','spread'),
 ('Equity recovered at refinance, min (%)','equity_recovered'),('Equity cash-in at refinance, max (%)','equity_cash_in'),
 ('Break-even occupancy, max (%)','breakeven_occupancy'),('Post-refi cash-on-cash, min (%)','post_refi_CoC'),
 ('Asking price over RLV, max (%)','asking_relative_to_supported_price'),('Equity ÷ TDC, max (%)','equity_TDC'),
 ('Levered IRR, min (%) *','IRR'),('Equity Multiple over the hold, min (x) *','equity_multiple')]


def _q(value):return None if value is None else {'numerator':str(value.numerator),'denominator':str(value.denominator)}


def _number(literal):
    if literal=='—':return None
    match=re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)(%| bps|x)',literal)
    if not match:raise ValidationError('unsupported exact source threshold literal')
    return Fraction(match[1])/({'%':100,' bps':10000,'x':1}[match[2]])


def read_documented_thresholds(raw):
    if type(raw)is not bytes or hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:
        raise ValidationError('experiment requires the exact preserved standards DOCX; no silent source replacement')
    with ZipFile(BytesIO(raw))as z:root=ET.fromstring(z.read('word/document.xml'))
    tables=root.findall('.//w:tbl',NS);matches=[]
    for index,table in enumerate(tables):
        rows=[[''.join(t.text or '' for t in cell.findall('.//w:t',NS))for cell in row.findall('w:tc',NS)]for row in table.findall('w:tr',NS)]
        if rows and rows[0]==HEADER:matches.append((index,rows))
    if len(matches)!=1:raise ValidationError('unique exact threshold table required')
    table_index,rows=matches[0]
    paragraphs=[''.join(t.text or ''for t in p.findall('.//w:t',NS))for p in root.findall('.//w:p',NS)]
    convention='Min = pass at or above; max = pass at or below; FAIL when Base is worse than the FAIL level.'
    convention_hits=[i for i,p in enumerate(paragraphs)if p.startswith(convention)]
    if len(convention_hits)!=1:raise ValidationError('exact inclusive-PASS/strict-FAIL convention required')
    if len(rows)!=11:raise ValidationError('source threshold inventory changed')
    metrics=[]
    for row_index,((label,metric),row)in enumerate(zip(ROWS,rows[1:]),1):
        if len(row)!=4 or row[0]!=label:raise ValidationError('exact source label and column mapping required')
        amounts=[_number(x)for x in row[1:]]
        metrics.append({'metric_id':metric,'source_label':label,'unit':'multiple'if metric=='equity_multiple'else'fraction',
            'pass_operator':'>='if ', min 'in label else'<=','fail_operator':'<'if ', min 'in label else'>',
            'pass_base':_q(amounts[0]),'pass_downside':_q(amounts[1]),'fail_base':_q(amounts[2]),
            'fail_downside':None,'source_literals':row[1:],
            'source_locators':{'pass_base':f'word/document.xml/table[{table_index}]/row[{row_index}]/cell[1]',
                'pass_downside':f'word/document.xml/table[{table_index}]/row[{row_index}]/cell[2]',
                'fail_base':f'word/document.xml/table[{table_index}]/row[{row_index}]/cell[3]'}})
    return {'source_sha256':SOURCE_SHA256,'source_table_index_zero_based':table_index,'locator_indices':'zero_based',
        'comparison_convention_locator':f'word/document.xml/descendant-paragraph[{convention_hits[0]}]',
        'comparison_convention_literal':convention,'thresholds_adopted':False,'source_author_authenticated':False,'metrics':metrics}


def parse_rehearsal(raw):
    if type(raw)is not bytes or not raw or len(raw)>1_048_576:raise ValidationError('bounded synthetic rehearsal JSON required')
    try:p=json.loads(raw.decode(),object_pairs_hook=_unique_object,parse_constant=_invalid_constant)
    except(UnicodeError,ValueError,RecursionError)as error:raise ValidationError('invalid rehearsal JSON')from error
    if type(p)is not dict or set(p)!={'schema','deal_id','case_id','run_id','required_scenarios','metric_values'}or p['schema']!=SCHEMA:
        raise ValidationError('exact synthetic rehearsal contract required')
    ContextSeed(deal_id=p['deal_id'],scenario_id='SYNTHETIC-explicit-inventory',run_id=p['run_id'],definition_set_revision='SYNTHETIC-matched-metadata-only')
    nonempty(p['case_id'],'case_id')
    if p['required_scenarios']not in (['Base'],['Base','Downside']):raise ValidationError('explicit Base-only or Base/Downside experiment required')
    if type(p['metric_values'])is not list or len(p['metric_values'])>20:raise ValidationError('bounded explicit metric records required')
    seen=set();known={metric for _,metric in ROWS}
    for row in p['metric_values']:
        if type(row)is not dict or set(row)!={'metric_id','scenario_id','value'}:raise ValidationError('exact metric record required')
        if type(row['metric_id'])is not str or type(row['scenario_id'])is not str:raise ValidationError('text identities required')
        pair=(row['metric_id'],row['scenario_id'])
        if pair in seen or pair[0]not in known or pair[1]not in p['required_scenarios']:raise ValidationError('duplicate or outside-inventory record')
        seen.add(pair);_fraction(row['value'])
    return p


def prepare_rehearsal(source_raw,case_raw):
    source=read_documented_thresholds(source_raw);p=parse_rehearsal(case_raw)
    values={(r['metric_id'],r['scenario_id']):r['value']for r in p['metric_values']}
    metrics=[];criteria=[]
    for metric in source['metrics']:
        for scenario in p['required_scenarios']:
            meta={'metric_id':metric['metric_id'],'scenario_id':scenario,
                'definition_ref':'SYNTHETIC-rehearsal-'+metric['metric_id']+'-v1','unit':metric['unit'],
                'quantity_kind':'scalar','currency':None,'period_ref':'SYNTHETIC-declared-matched-scope-v1',
                'applicability':'applicable','applicability_evidence_ref':None}
            if (metric['metric_id'],scenario)in values:metrics.append(dict(meta,value=values[(metric['metric_id'],scenario)]))
            passing=metric['pass_base'if scenario=='Base'else'pass_downside']
            failing=metric['fail_base'if scenario=='Base'else'fail_downside']
            criteria.append(dict(meta,pass_condition={'operator':metric['pass_operator']if passing is not None else None,'threshold':passing},
                fail_condition={'operator':metric['fail_operator']if failing is not None else None,'threshold':failing}))
    case={'schema':SCREEN_SCHEMA,'context':{'deal_id':p['deal_id'],'scenario_id':'SYNTHETIC-explicit-inventory',
        'run_id':p['run_id'],'definition_set_revision':'SYNTHETIC-matched-metadata-only'},'case_id':p['case_id'],
        'criteria_revision':'SYNTHETIC-document-experiment-'+SOURCE_SHA256,'criteria_status':'synthetic_fixture_only',
        'required_metrics':[m['metric_id']for m in source['metrics']],'required_scenarios':p['required_scenarios'],
        'metric_values':metrics,'criteria':criteria,'aggregation_rule':AGGREGATION,'hypothetical_band_policy':None}
    return source,(canonical(case)+'\n').encode()


def rehearse(source_raw,case_raw):
    source,screen_raw=prepare_rehearsal(source_raw,case_raw);run=simulate_screening(screen_raw)
    return {'component':'T14','purpose':'source_backed_synthetic_comparator_experiment','source_profile':source,'experiment_engine_sha256':ENGINE_SHA256,
        'comparator_engine_sha256':run.payload['engine_sha256'],'definition_sources':run.payload['definition_sources'],
        'user_policy_reference':run.payload['user_policy_reference'],
        'rehearsal_source_sha256':hashlib.sha256(case_raw).hexdigest(),'screening_source_sha256':hashlib.sha256(screen_raw).hexdigest(),
        'screening_run_sha256':run.sha256,'scope':'Base-only comparator experiment'if run.payload['required_scenarios']==['Base']else'Base/Downside compatibility experiment',
        'simulation_result':run.payload['simulation_result'],'simulation_blockers':run.payload['simulation_blockers'],
        'comparison_states':[{'metric_id':r['metric_id'],'scenario_id':r['scenario_id'],'state':r['state'],'blockers':r['blockers']}for r in run.payload['comparisons']],
        'known_integration_limits':['current canonical comparator requires PASS and FAIL conditions for each applicable scenario',
            'source defines FAIL Base only; FAIL Downside remains absent',
            'source Asking/RLV PASS Downside dash is not interpreted as approved non-applicability'],
        'metric_values_are_fictitious':True,'metric_metadata_is_synthetic_declared_compatible_only':True,
        'metric_values_financially_verified':False,'thresholds_adopted':False,'full_miniuw_completed':False,
        'decision':'PENDING','review_authenticated':False,'production_authorized':False}
