"""T111 single-page worksheet gate over verified synthetic T110 cash layout."""
from pathlib import Path
from .drafts import ValidationError,canonical,digest
from .scheduled_expense_case import sha
from .worksheet_settled_output import WorksheetSettledRun,assemble_worksheet_settled_output,DEFINITION
from .phased_settled_report import _render_verified as _cash_layout,ENGINE_SHA256 as LAYOUT_ENGINE_SHA256
from .synthetic_onepager import _pdf,_pdf_string,PreviewLayoutError
from .v1_report import V1Report

ENGINE_SHA256=sha(Path(__file__).read_bytes())


def _render_verified(run):
    p=run.payload;base=_cash_layout(run);m=base.manifest;check=p['worksheet_reconciliation'];commands=[b'0.06 0.17 0.25 rg 24 524 744 64 re f']
    for row in m['display_spans']:
        y=row['y']
        if y==566:row['text']='MINI-UW | HOJA, RENTA Y VENTA'
        elif y==546:
            row['text']='PENDIENTE | Hoja '+('cotejada'if p['worksheet_gate_open']else'bloqueada')+' | equity agregado sintetico';row['result_pointers']=['/decision','/worksheet_gate_open']
        elif y==110:
            row['text']='55 campos: '+str(check['counts'].get('MATCHED_REPRESENTATION',0))+' coinciden; '+str(check['counts'].get('MISSING_BOTH',0))+' faltan. Semantica pendiente. Detalle: current-results.json.';row['result_pointers']=['/worksheet_reconciliation/counts']
        elif row['text'].startswith('Resultado T110 SHA256:'):row['text']='Resultado T111 SHA256: '+run.sha256
        x,size,width=row['x'],row['font_size'],row['width']
        if len(row['text'])*size*.6>width or x<24 or x+width>768 or y<25 or y+size>588:raise PreviewLayoutError('worksheet/settled span exceeds bounded one-page layout')
        commands.append(b'1 1 1 rg'if y>=532 else b'0.06 0.17 0.25 rg')
        bold=y in(566,546,476,457,440,214,224,294,164,40)
        commands.append(f'BT /{"F2"if bold else"F1"} {size} Tf 1 0 0 1 {x} {y} Tm ('.encode()+_pdf_string(row['text'])+b') Tj ET')
    pdf=_pdf(commands);m.update(component='T111-report',engine_sha256=ENGINE_SHA256,definition_sha256=sha(DEFINITION.read_bytes()),layout_engine_sha256=LAYOUT_ENGINE_SHA256,layout_manifest_sha256=base.manifest_sha256,
        result_sha256=run.sha256,pdf_sha256=sha(pdf),worksheet_gate_open=p['worksheet_gate_open'],worksheet_source_sha256=check['source_hashes']['workbook_sha256'],worksheet_values_adopted=False,worksheet_financial_semantics_completed=False)
    value=canonical(m);return V1Report(pdf,value,digest(value))


def render_worksheet_settled_output(raw,run):
    if type(run)is not WorksheetSettledRun or assemble_worksheet_settled_output(raw)!=run:raise ValidationError('worksheet/settled page requires complete source and worksheet replay')
    return _render_verified(run)
