"""T111 compare source-bound worksheet declarations without adopting financial mappings."""
from dataclasses import dataclass,asdict
from pathlib import Path
import base64,binascii,copy,json
from .drafts import ValidationError,ContextSeed,canonical,digest,nonempty
from .expense_cash_detail import _json,_exact
from .expense_checked_lifecycle import _utf8
from .scheduled_expense_case import sha
from .phased_settled_output import assemble_phased_settled_output,required_sources as parent_requirements
from .inputsheet import inspect_synthetic_input_sheet,layout
from .worksheet_case_output import _cell_value,SCOPE
from .v1_case import catalog
from .debt_service import _fraction
from .evidence_currency import evaluate_evidence_currency,timestamp,_sha
from .intake import MAX_BYTES as MAX_WORKBOOK_BYTES

ROOT=Path(__file__).resolve().parents[2]
ENGINE_SHA256=sha(Path(__file__).read_bytes())
DEFINITION=ROOT/'docs/technical-implementation-T111.md'


def parse_claims(raw):
    p=_json(raw,1048576)
    _exact(p,{'schema','context','case_id','case_revision','as_of_UTC','source_ref','original_inputs'})
    if p['schema']!='miniuw.synthetic-original-worksheet-claims.v1':raise ValidationError('exact original worksheet claim catalogue required')
    if type(p['context'])is not dict:raise ValidationError('explicit worksheet context required')
    try:ContextSeed(**p['context'])
    except TypeError as error:raise ValidationError('exact worksheet context required')from error
    nonempty(p['case_id'],'case_id')
    if not p['case_id'].startswith('SYNTHETIC-')or len(p['case_id'])>64 or any(ord(c)<32 or ord(c)==127 for c in p['case_id']):raise ValidationError('bounded printable synthetic case ID required')
    if type(p['case_revision'])is not int or p['case_revision']<1:raise ValidationError('explicit positive worksheet revision required')
    timestamp(p['as_of_UTC'])
    if p['source_ref']is not None:nonempty(p['source_ref'],'source_ref')
    if type(p['original_inputs'])is not list or [r.get('field_id')for r in p['original_inputs']if type(r)is dict]!=[r['field_id']for r in catalog()[0]]:raise ValidationError('exact 55 claims in original order required')
    for row in p['original_inputs']:
        _exact(row,{'field_id','value','unit','period_ref','source_ref'})
        if row['value']is not None and type(row['value'])is not str:_fraction(row['value'])
        for k in ('unit','period_ref','source_ref'):
            if row[k]is not None:nonempty(row[k],k)
    return p


def parse_binding(raw):
    p=_json(raw,65536)
    _exact(p,{'schema','scope','binding_id','phased_settled_source_sha256','claims_source_sha256','workbook_sha256','context','case_id','case_revision','as_of_UTC','source_ref'})
    if p['schema']!='miniuw.synthetic-worksheet-settled-binding.v1'or p['scope']!=SCOPE:raise ValidationError('exact worksheet/settled claim-only binding required')
    nonempty(p['binding_id'],'binding_id')
    if not p['binding_id'].startswith('SYNTHETIC-'):raise ValidationError('synthetic binding required')
    for k in ('phased_settled_source_sha256','claims_source_sha256','workbook_sha256'):_sha(p[k])
    if type(p['context'])is not dict or type(p['case_revision'])is not int or p['case_revision']<1:raise ValidationError('explicit context and positive revision required')
    for k in ('case_id','as_of_UTC'):nonempty(p[k],k)
    if p['source_ref']is not None:nonempty(p['source_ref'],'source_ref')
    return p


def parse_source(raw):
    p=_json(raw,32*1024*1024)
    _exact(p,{'schema','phased_settled_source_utf8','claims_source_utf8','workbook_base64','binding_source_utf8','registry_source_utf8','evaluated_as_of_UTC'})
    if p['schema']!='miniuw.synthetic-worksheet-settled-output.v1':raise ValidationError('exact worksheet settled source profile required')
    for k,limit in [('phased_settled_source_utf8',24*1024*1024),('claims_source_utf8',1048576),('binding_source_utf8',65536),('registry_source_utf8',1048576)]:_utf8(p[k],limit)
    timestamp(p['evaluated_as_of_UTC']);value=p['workbook_base64']
    if type(value)is not str or len(value)>4*((MAX_WORKBOOK_BYTES+2)//3):raise ValidationError('bounded base64 worksheet required')
    try:workbook=base64.b64decode(value,validate=True)
    except(ValueError,binascii.Error)as error:raise ValidationError('invalid worksheet base64')from error
    if not workbook or len(workbook)>MAX_WORKBOOK_BYTES:raise ValidationError('bounded nonempty worksheet required')
    return p,workbook


def required_sources(raw):
    p,workbook=parse_source(raw);rows=parent_requirements(p['phased_settled_source_utf8'].encode())
    def add(path,data):rows.append(dict(requirement_id=path,source_locator=path,source_sha256=sha(data)))
    for k in ('phased_settled_source_utf8','claims_source_utf8','binding_source_utf8'):add('/T111/'+k,p[k].encode())
    add('/T111/worksheet',workbook)
    for name in ('worksheet_settled_output','worksheet_case_output','inputsheet','workbooks','normalization','v1_case'):add('/T111/engines/'+name,(ROOT/('src/miniuw_foundation/'+name+'.py')).read_bytes())
    add('/T111/original_layout',(ROOT/'src/miniuw_foundation/data/input-sheet-layout-v1.json').read_bytes());add('/T111/definition',DEFINITION.read_bytes())
    if len(rows)>256 or len({r['requirement_id']for r in rows})!=len(rows):raise ValidationError('bounded unique complete worksheet source inventory required')
    return rows


def check_worksheet(parent_raw,claims_raw,workbook,binding_raw,parent_payload):
    claims=parse_claims(claims_raw);b=parse_binding(binding_raw);inspection=inspect_synthetic_input_sheet(workbook);cells=inspection.cells;issues=[];rows=[];counts={}
    expected=dict(phased_settled_source_sha256=sha(parent_raw),claims_source_sha256=sha(claims_raw),workbook_sha256=sha(workbook),context=claims['context'],case_id=claims['case_id'],case_revision=claims['case_revision'],as_of_UTC=claims['as_of_UTC'])
    for k,v in expected.items():
        if b[k]!=v:issues.append('binding_'+k+'_mismatch')
    if claims['context']!=parent_payload['context']:issues.append('claims_and_parent_context_mismatch')
    if claims['case_id']!=parent_payload['context']['deal_id']:issues.append('claims_ID_differs_from_parent_deal_ID')
    if claims['as_of_UTC']!=parent_payload['evaluated_as_of_UTC']:issues.append('claims_and_parent_UTC_mismatch')
    for label,value in [('claims',claims['source_ref']),('binding',b['source_ref'])]:
        if value is None:issues.append(label+'_source_ref_missing')
    for ref,value in [('B3',claims['case_id']),('E3',claims['as_of_UTC'])]:
        if cells.get(ref,{}).get('kind')!='text'or cells[ref]['literal']!=value:issues.append('worksheet_metadata_mismatch:'+ref)
    fields={f['field_id']:f for f in layout()['fields']}
    for i,claim in enumerate(claims['original_inputs']):
        f=fields[claim['field_id']];cell=cells[f['value_cell']];unit=cells[f['unit_cell']]['literal'];value,local=_cell_value(cell,dict(f,unit_literal=unit))
        if local:state='PENDING'
        elif value is None and claim['value']is None:state='MISSING_BOTH'
        elif (type(value)is dict and type(claim['value'])is dict and _fraction(value,1300)==_fraction(claim['value'],1300))or canonical(value)==canonical(claim['value']):state='MATCHED_REPRESENTATION'
        else:state='CONFLICT';local=['worksheet_value_differs_from_claim']
        if claim['unit']is not None and claim['unit']!=unit:local.append('worksheet_unit_literal_differs_from_claim');state='CONFLICT'
        if claim['value']is not None and claim['source_ref']is None:local.append('declared_value_source_ref_missing');state='PENDING'
        counts[state]=counts.get(state,0)+1;issues.extend(claim['field_id']+':'+v for v in local)
        rows.append(dict(field_id=claim['field_id'],cell=f['value_cell'],worksheet_source_sha256=inspection.source_sha256,worksheet_locator='xlsx:sheet:Inputs:cell:'+f['value_cell'],worksheet_cell=cell,
            source_description_cell=f['source_text_cell'],source_description=cells.get(f['source_text_cell']),unit_literal=unit,decoded_representation=value,claim=claim,
            claim_pointer='/claims_source_utf8::json/original_inputs/'+str(i)+'/value',state=state,blockers=local,financial_semantics_verified=False))
    return dict(state='PENDING'if issues else'matched_claims_with_pending_financial_semantics',rows=rows,counts=counts,blockers=sorted(set(issues)),source_hashes={k:v for k,v in expected.items()if k.endswith('_sha256')},binding_metadata={k:v for k,v in expected.items()if not k.endswith('_sha256')},
        sheet_metadata={ref:cells.get(ref)for ref in('B3','E3')},worksheet_values_adopted=False,projection_computed_from_55_claims=False,financial_field_mapping_completed=False,source_authority_authenticated=False)


@dataclass(frozen=True)
class WorksheetSettledRun:
    payload_json:str
    sha256:str
    @property
    def payload(self):return json.loads(self.payload_json)


def assemble_worksheet_settled_output(raw):
    p,workbook=parse_source(raw);parent_raw=p['phased_settled_source_utf8'].encode();parent=assemble_phased_settled_output(parent_raw);result=copy.deepcopy(parent.payload)
    check=check_worksheet(parent_raw,p['claims_source_utf8'].encode(),workbook,p['binding_source_utf8'].encode(),result);requirements=required_sources(raw);registry=evaluate_evidence_currency(p['registry_source_utf8'].encode(),p['evaluated_as_of_UTC']);r=registry.payload;gate=[]
    if sorted(requirements,key=lambda v:v['requirement_id'])!=sorted([v['requirement']for v in r['requirements']],key=lambda v:v['requirement_id']):gate.append('complete_exact_worksheet_settled_inventory_mismatch')
    if r['context']!=result['context']:gate.append('worksheet_registry_context_mismatch')
    if r['state']!='current_synthetic_evidence':gate.append('worksheet_settled_evidence_not_current')
    if p['evaluated_as_of_UTC']!=result['evaluated_as_of_UTC']:gate.append('worksheet_and_parent_evaluation_UTC_mismatch')
    if check['blockers']:gate.append('worksheet_claim_reconciliation_blocked')
    if result['current_project_return_story']is None:gate.append('parent_phased_settled_output_blocked')
    result['blockers']['gate']+=gate;result['blockers']['evidence']+=r['blockers'];result['blockers']['calculation']['worksheet']=check['blockers'];compatible=not result['blockers']['gate']
    if not compatible:
        for k in list(result):
            if k.startswith('current_'):result[k]=None
    result.update(component='T111',engine_sha256=ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),source_sha256=sha(raw),parent_phased_input_sha256=sha(parent_raw),parent_phased_run_sha256=parent.sha256,
        parent_phased_registry_run_sha256=parent.payload['registry_run']['sha256'],registry_source_sha256=sha(p['registry_source_utf8'].encode()),registry_run=asdict(registry),required_sources=requirements,source_requirements_checked=len(requirements),
        worksheet_reconciliation=check,worksheet_gate_open=not check['blockers'],worksheet_values_adopted=False,projection_computed_from_55_claims=False,worksheet_financial_semantics_completed=False,
        state='current_synthetic_worksheet_settled_output'if compatible else'PENDING',synthetic_complete_source_evidence_current=compatible,parent_result_used_as_current_fallback=False)
    value=canonical(result);return WorksheetSettledRun(value,digest(value))
