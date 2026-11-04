"""T96 one-page annual cash presentation after exact T94 source-gate replay.

Recompose the pinned T95 page spans; retain all financial producers and sources.
"""
from pathlib import Path

from .drafts import ValidationError, canonical, digest
from .policy_renewal_case import assemble_policy_renewal_case, PolicyRenewalCaseRun
from .policy_renewal_artifacts import render_policy_renewal_report, ENGINE_SHA256 as PARENT_ENGINE_SHA256
from .scheduled_expense_case import sha
from .synthetic_onepager import _pdf, _pdf_string, PreviewLayoutError
from .v1_report import V1Report, amount

ENGINE_SHA256 = sha(Path(__file__).read_bytes())
DEFINITION = Path(__file__).resolve().parents[2] / 'docs/technical-implementation-T96.md'
STORY = '/current_project_return_story'


def _compose_verified(run, parent):
    payload = run.payload
    story = payload['current_project_return_story']
    manifest = parent.manifest
    spans = manifest['display_spans']
    context = [row for row in spans if row['result_pointers'] == ['/evaluated_as_of_UTC']]
    if len(context) != 1:
        raise ValidationError('compatible T95 context span required')
    context = context[0]
    if story is None:
        context['text'] = 'UTC '+payload['evaluated_as_of_UTC']+' | Equity: proyecto | Moneda/ventana actuales: pendientes'
    else:
        if story['equity_level'] != 'aggregate_project_equity':
            raise ValidationError('explicit aggregate project-equity scope required')
        window = story['cash_horizon']
        context['text'] = ('UTC '+payload['evaluated_as_of_UTC']+' | Equity: proyecto | Moneda '+story['currency']+
                           ' | Ventana '+window['start']+' a '+window['end'])
    context['result_pointers'] = ['/evaluated_as_of_UTC',STORY+'/equity_level',STORY+'/currency',STORY+'/cash_horizon']
    headings = [row for row in spans if row['text'] == 'CAPITAL / CAJA ANUAL']
    if len(headings) != 1:
        raise ValidationError('compatible T95 annual cash heading required')
    headings[0].update(text='CAJA ANUAL: A aporte, C cobro, N neto, O operativo',font_size=6.7)
    years = [] if story is None else story['annual_cash_receipts']
    annual = [row for row in spans if any(ref.startswith(STORY+'/annual_cash_receipts/') for ref in row['result_pointers'])]
    if len(annual) != len(years):
        raise ValidationError('exact supplied annual cash row inventory required')
    for index,(row,year) in enumerate(zip(annual,years)):
        row['text'] = (str(year['calendar_cash_receipt_year'])+' A'+amount(year['gross_contributions'])+
                       ' C'+amount(year['gross_distributions'])+' N'+amount(year['net_equity_cash'])+
                       ' O'+amount(year['operating_distributions_only'])+' CoC:'+amount(year['conditional_coc']))
        row['result_pointers'] = [STORY+'/annual_cash_receipts/'+str(index)+'/'+key for key in
            ('calendar_cash_receipt_year','gross_contributions','gross_distributions','net_equity_cash',
             'operating_distributions_only','conditional_coc','declared_capital_base')]
    # Rebuild the same bounded page from its verified spans, retaining header colors.
    commands = [b'0.06 0.17 0.25 rg 24 524 744 64 re f 1 1 1 rg']
    if len(spans) < 3 or any(row['y'] < 524 for row in spans[:3]):
        raise ValidationError('compatible T95 three-span page header required')
    for index,row in enumerate(spans):
        if index == 3:
            commands.append(b'0.06 0.17 0.25 rg')
        x,y,size,width = (row[key] for key in ('x','y','font_size','width'))
        if len(row['text'])*size*.6 > width or x<24 or x+width>768 or y<25 or y+size>588:
            raise PreviewLayoutError('T96 one-page span exceeds explicit layout budget')
        # T95 has no stored font-weight flag; these existing headings are explicit.
        bold = index<3 or row['text'] in ('Aportes brutos','Cobros brutos','Resultado de caja','Equity Multiple',
            'APORTES Y COBROS CON FECHAS'+(' ('+story['currency']+')' if story else ''),
            'METRICA / VALOR / CRITERIO (P/F)','BASE DECLARADA / REFI','RIESGOS Y ALCANCE',headings[0]['text'])
        if row['font_size'] == 12 or row['text'].startswith(('FORMATO:','PRUEBA SINTETICA.')):
            bold = True
        commands.append(f'BT /{"F2" if bold else "F1"} {size} Tf 1 0 0 1 {x} {y} Tm ('.encode()+_pdf_string(row['text'])+b') Tj ET')
    pdf = _pdf(commands)
    manifest.update(component='T96',engine_sha256=ENGINE_SHA256,parent_policy_report_engine_sha256=PARENT_ENGINE_SHA256,
                    parent_report_manifest_sha256=parent.manifest_sha256,definition_sha256=sha(DEFINITION.read_bytes()),
                    input_sha256=payload['case_source_sha256'],result_sha256=run.sha256,pdf_sha256=sha(pdf),
                    annual_cash_report_scope='supplied_calendar_cash_receipt_window_not_verified_full_operating_year',
                    new_financial_calculations=False,capital_stock_derived=False,personal_return_verified=False,
                    financial_publication_authorized=False,decision='PENDING')
    text = canonical(manifest)
    return V1Report(pdf,text,digest(text))


def render_investor_onepage(raw, run):
    if type(run) is not PolicyRenewalCaseRun or assemble_policy_renewal_case(raw) != run:
        raise ValidationError('T96 investor page requires exact complete T94 source-gate replay')
    return _compose_verified(run,render_policy_renewal_report(raw,run))
