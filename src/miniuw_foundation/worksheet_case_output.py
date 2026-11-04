"""T103 exact original-layout worksheet/case reconciliation, without value adoption."""
from dataclasses import dataclass
from pathlib import Path
import json
from .drafts import ValidationError,canonical,digest,nonempty
from .expense_cash_detail import _json,_exact
from .scheduled_expense_case import sha
from .inputsheet import inspect_synthetic_input_sheet,layout
from .normalization import NumericProfile,_number,ENGINE_SHA256 as NUMERIC_ENGINE_SHA256
from .debt_service import _fraction,rational
from .irr_interval_output import IRRIntervalRun,assemble_irr_interval_output,_render_verified as _parent_report
from .v1_report import V1Report
from .synthetic_onepager import _pdf,_pdf_string,PreviewLayoutError

ENGINE_SHA256=sha(Path(__file__).read_bytes())
DEFINITION=Path(__file__).resolve().parents[2]/'docs/technical-implementation-T103.md'
LAYOUT=Path(__file__).parent/'data/input-sheet-layout-v1.json'
READER=Path(__file__).parent/'inputsheet.py'
WORKBOOK_READER=Path(__file__).parent/'workbooks.py'
SCHEMA='miniuw.synthetic-worksheet-case-binding.v1'
SCOPE='original_55_claim_representation_only_no_financial_mapping'


def parse_binding(raw):
    p=_json(raw,65536)
    _exact(p,{'schema','binding_id','scope','case_sha256','workbook_sha256','context','case_id','case_revision','as_of_UTC','source_ref'})
    if p['schema']!=SCHEMA or p['scope']!=SCOPE:raise ValidationError('explicit worksheet claim-only binding profile required')
    nonempty(p['binding_id'],'binding_id')
    if not p['binding_id'].startswith('SYNTHETIC-'):raise ValidationError('synthetic binding ID required')
    for key in('case_sha256','workbook_sha256'):
        value=p[key]
        if type(value)is not str or len(value)!=64 or any(c not in'0123456789abcdef'for c in value):raise ValidationError('exact lowercase source SHA256 required')
    if type(p['context'])is not dict or type(p['case_revision'])is not int or p['case_revision']<1:
        raise ValidationError('explicit case context/revision required')
    for key in('case_id','as_of_UTC'):nonempty(p[key],key)
    if p['source_ref']is not None:nonempty(p['source_ref'],'source_ref')
    return p


def _cell_value(cell,field):
    kind=cell['kind']
    if kind in('missing','blank'):return None,[]
    if kind=='text':return cell['literal'],[]
    if kind!='numeric_lexeme':return None,['formula_or_error_not_resolved']
    profile=NumericProfile(profile_id='SYNTHETIC-T103-'+field['field_id'],definition_revision='decimal-representation-only-v1',
        slot_id=field['field_id'],source_definition_ref='input-sheet-layout-v1',decimal_mark='.',notation='decimal',
        trim_outer_whitespace=False,source_unit_literal=field['unit_literal'],target_unit=field['unit_literal'],
        quantity_kind='scalar',currency_literal=None,period_literal=None)
    value,error=_number(cell['literal'],profile)
    return(None,[error])if error else(rational(value),[])


def _reconcile(case_raw,workbook_raw,binding_raw,parent):
    binding=parse_binding(binding_raw);inspection=inspect_synthetic_input_sheet(workbook_raw);cells=inspection.cells;p=parent.payload
    blockers=[]
    for key,expected in(('case_sha256',sha(case_raw)),('workbook_sha256',sha(workbook_raw)),('context',p['context']),
        ('case_id',p['case_id']),('case_revision',p['case_revision']),('as_of_UTC',p['evaluated_as_of_UTC'])):
        if binding[key]!=expected:blockers.append('binding_'+key+'_mismatch')
    if binding['source_ref']is None:blockers.append('binding_source_ref_missing')
    for ref,expected in(('B3',p['case_id']),('E3',p['evaluated_as_of_UTC'])):
        cell=cells.get(ref,{})
        if cell.get('kind')!='text'or cell.get('literal')!=expected:blockers.append('worksheet_metadata_mismatch:'+ref)
    rows=[];counts={}
    fields={f['field_id']:f for f in layout()['fields']}
    if set(fields)!={c['field_id']for c in p['original_inputs']}or len(p['original_inputs'])!=55:raise ValidationError('exact original field catalog required')
    for index,claim in enumerate(p['original_inputs']):
        field=fields[claim['field_id']]
        cell=cells[field['value_cell']];unit=cells[field['unit_cell']]['literal']
        value,issues=_cell_value(cell,dict(field,unit_literal=unit))
        if issues:state='PENDING'
        elif value is None and claim['value']is None:state='MISSING_BOTH'
        elif (type(value)is dict and type(claim['value'])is dict and _fraction(value,1300)==_fraction(claim['value'],1300))or canonical(value)==canonical(claim['value']):state='MATCHED_REPRESENTATION'
        else:state='CONFLICT';issues=['worksheet_value_differs_from_case_claim']
        counts[state]=counts.get(state,0)+1
        blockers.extend(claim['field_id']+':'+reason for reason in issues)
        rows.append(dict(field_id=claim['field_id'],cell=field['value_cell'],worksheet_source_sha256=inspection.source_sha256,
            worksheet_locator='xlsx:sheet:Inputs:cell:'+field['value_cell'],worksheet_cell=cell,
            source_description_cell=field['source_text_cell'],source_description=cells.get(field['source_text_cell']),
            unit_literal=unit,decoded_representation=value,case_value=claim['value'],case_unit=claim['unit'],
            case_pointer='/scheduled_case_utf8::json/base_case_utf8::json/original_inputs/'+str(index)+'/value',
            case_original_state=claim['state'],case_mapping_basis_ref=claim['mapping_basis_ref'],
            state=state,blockers=issues,financial_semantics_verified=False))
    return dict(state='PENDING'if blockers else'matched_claims_with_pending_semantics',rows=rows,counts=counts,
        blockers=sorted(set(blockers)),source_hashes=dict(case=sha(case_raw),workbook=sha(workbook_raw),binding=sha(binding_raw)),
        binding_id=binding['binding_id'],sheet_metadata={ref:cells.get(ref)for ref in('B3','E3')},
        financial_field_mapping_completed=False,source_authority_authenticated=False,case_modified=False,worksheet_values_adopted=False)


@dataclass(frozen=True)
class WorksheetCaseRun:
    payload_json:str
    sha256:str
    parent_run:IRRIntervalRun
    @property
    def payload(self):return json.loads(self.payload_json)


def _from_verified_parent(case_raw,workbook_raw,binding_raw,parent):
    check=_reconcile(case_raw,workbook_raw,binding_raw,parent);p=parent.payload
    if check['blockers']:
        p['screening_simulation_result']='PENDING';p['screening_run_sha256']=None
        p['current_project_return_story']=None;p['current_projection_run_sha256']=None;p['current_IRR_solver_result_sha256']=None
        p['latest_capital_snapshot_index']=None;p['latest_capital_state']='PENDING';p['capital_visibility']=[]
        p['irr_recalculation']=None;p['irr_output_state']='PENDING'
        for metric in p['metrics']:
            metric.update(value=None,value_state='PENDING',reason='Hoja y expediente sin conciliar',comparison_state='PENDING',
                comparison_blockers=['worksheet_case_reconciliation_pending'])
        p['IRR_interval_comparison'].update(row_state='PENDING',relations={},enclosure=None,
            blockers=['worksheet_case_reconciliation_pending'])
    p['blockers']['worksheet_case']=check['blockers']
    p.update(component='T103',title='Mini-UW v1 | Hoja y expediente',purpose='synthetic_original_worksheet_current_case_check',engine_sha256=ENGINE_SHA256,
        definition_sha256=sha(DEFINITION.read_bytes()),worksheet_reader_sha256=sha(READER.read_bytes()),
        workbook_reader_sha256=sha(WORKBOOK_READER.read_bytes()),worksheet_layout_sha256=sha(LAYOUT.read_bytes()),
        numeric_decoder_sha256=NUMERIC_ENGINE_SHA256,parent_interval_run_sha256=parent.sha256,
        worksheet_reconciliation=check,worksheet_gate_open=not check['blockers'],
        state='PENDING'if p['current_project_return_story']is None else'computed_synthetic_profile_with_pending_decision',
        current_figures_are_parent_fallback=False,case_or_recipe_automatically_updated=False,worksheet_values_adopted=False,
        financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')
    value=canonical(p);return WorksheetCaseRun(value,digest(value),parent)


def assemble_worksheet_case(case_raw,workbook_raw,binding_raw):
    parse_binding(binding_raw);inspect_synthetic_input_sheet(workbook_raw)
    return _from_verified_parent(case_raw,workbook_raw,binding_raw,assemble_irr_interval_output(case_raw))


def _render_verified(run):
    p=run.payload
    proxy=IRRIntervalRun(run.payload_json,run.sha256,run.parent_run.parent_run)
    report=_parent_report(proxy);m=report.manifest;commands=[b'0.06 0.17 0.25 rg 24 524 744 64 re f 0.06 0.17 0.25 rg']
    for row in m['display_spans']:
        y=row['y']
        if y==546:row['text']='PENDIENTE | Hoja '+('cotejada'if p['worksheet_gate_open']else'bloqueada')+' | equity agregado sintetico'
        elif y==82:row['text']='Hoja SHA256: '+p['worksheet_reconciliation']['source_hashes']['workbook']
        elif row['text'].startswith('Resultado T101 SHA256: '):row['text']='Resultado T103 SHA256: '+run.sha256
        x,size,width=row['x'],row['font_size'],row['width']
        if len(row['text'])*size*.6>width or x<24 or x+width>768 or y<25 or y+size>588:raise PreviewLayoutError('T103 span exceeds one-page budget')
        commands.append(b'1 1 1 rg'if y>=532 else b'0.06 0.17 0.25 rg')
        bold=y in(566,546,476,457,440,215,171,179,116,40)
        commands.append(f'BT /{"F2"if bold else"F1"} {size} Tf 1 0 0 1 {x} {y} Tm ('.encode()+_pdf_string(row['text'])+b') Tj ET')
    pdf=_pdf(commands)
    m.update(component='T103',engine_sha256=ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),
        result_component='T103',result_sha256=run.sha256,pdf_sha256=sha(pdf),parent_interval_run_sha256=run.parent_run.sha256,
        parent_composition_manifest_sha256=report.manifest_sha256,worksheet_gate_open=p['worksheet_gate_open'],
        worksheet_source_hashes=p['worksheet_reconciliation']['source_hashes'],worksheet_values_adopted=False,
        financial_field_mapping_completed=False,decision='PENDING')
    value=canonical(m);return V1Report(pdf,value,digest(value))


def render_worksheet_case(case_raw,workbook_raw,binding_raw,run):
    if type(run)is not WorksheetCaseRun or assemble_worksheet_case(case_raw,workbook_raw,binding_raw)!=run:
        raise ValidationError('worksheet page requires exact case, workbook and binding replay')
    return _render_verified(run)
