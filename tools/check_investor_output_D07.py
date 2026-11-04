"""D07 read-only investor-output contract and synthetic return consistency review."""
import argparse
import copy
import csv
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import sys

from check_reference_package import local_file, require, PackageError
from check_dependency_structure_D05 import resolve_pointer, source_function
from check_blocking_structure_D06 import definitions, probe_source

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
DIRECTORY = 'docs/current-structure/'
SNAPSHOT = DIRECTORY + 'MiniUW_Salida_Inversor_D07.json'
CSV = DIRECTORY + 'MiniUW_Salida_Inversor_D07.csv'
RECORD = DIRECTORY + 'D07-structural-validation.json'
CASES = ['templates/miniuw-v1-policy-renewal-case.json',
         'templates/miniuw-v1-policy-renewal-twelve-case.json']
FLOW = 'docs/review/information-flow-summary-FLOW02.json'
STORY = '/current_project_return_story'
EXAMPLE = 'docs/review/miniuw-v1-investor-output-example/'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def rational(value):
    return dict(numerator=str(value.numerator), denominator=str(value.denominator))


def fraction(value):
    require(type(value) is dict and set(value) == {'numerator','denominator'}, 'exact rational value required')
    return Fraction(int(value['numerator']),int(value['denominator']))


def output_definitions():
    def field(fid,label,kind,key,selector,question,meaning,presentation='matched_spans_only'):
        return dict(field_id=fid,label=label,quantity_kind=kind,source_pointer=STORY+'/'+key,
                    selector=selector,requirement_document=FLOW,
                    requirement_pointer=('/steps/7/description' if question is None else '/investor_return_questions/'+str(question)),
                    definition=meaning,presentation_scope=presentation)
    return [
        field('R01','Moneda','metadata','currency','direct',None,'Moneda declarada; no derivar USD de un símbolo.'),
        field('R02','Alcance del equity','metadata','equity_level','direct',None,'Equity agregado del proyecto; no reparto personal.'),
        field('R03','Ventana de caja','dates','cash_horizon','direct',None,'Fechas declaradas y exclusión de cobros posteriores.'),
        field('R04','Aportes iniciales y fechas','cash','dated_events','initial_capital',0,'Movimientos brutos iniciales; conservar fecha y fuente.'),
        field('R05','Aportes adicionales y fechas','cash','dated_events','additional_capital',0,'Todos los adicionales, incluidos ceros explícitos; cash-in refi separado.'),
        field('R06','Cobros operativos y fechas','cash','dated_events','operating_distribution',5,'Cobro de equity conciliado; no equivale a NOI.'),
        field('R07','Cobro neto refi y fechas','cash','dated_events','net_refinance_distribution',1,'En esta ruta sin refi: total explícito cero y ningún mes de refi inventado.'),
        field('R08','Cash-in refi y fechas','cash','dated_events','refinance_cash_in',2,'Aporte separado; cero sólo en esta ruta suministrada sin refi.'),
        field('R09','Cobro neto venta y fecha','cash','dated_events','net_sale_distribution',6,'Residual neto conciliado; no precio bruto o valor retenido.'),
        field('R10','Aportes brutos totales','cash','gross_contributions','direct',0,'Suma bruta de aportes; no netear contra distribuciones.'),
        field('R11','Cobros brutos totales','cash','gross_distributions','direct',7,'Suma bruta de cobros; no suma valor del equity retenido.'),
        field('R12','Resultado neto de caja','cash','net_cash_profit','direct',7,'Cobros menos aportes dentro de la ventana; no pérdida económica definitiva.'),
        field('R13','Equity multiple','ratio','equity_multiple','direct',7,'Cobros brutos / aportes brutos positivos; múltiplo, no tasa anual.'),
        field('R14','TIR anual y selección','intervals','annual_irr_roots','irr',7,'Conservar todas las raíces/intervalos y selección nula. No fabricar un punto.'),
        field('R15','Referencia por 10 y base','normalization','normalized_story','direct',None,'Escala sobre base explícita de aportes del proyecto; no participación personal.', 'reference_basis_and_totals_only'),
        field('R16','Capital aún invertido','stock','capital_snapshots','capital_still_invested',3,'Stock declarado con fecha/base/fuente; no aportes menos cobros.'),
        field('R17','Equity retenido','stock','capital_snapshots','retained_equity_value',4,'Valor declarado, separado de efectivo cobrado.'),
        field('R18','Caja neta anual','annual_cash','annual_cash_receipts','annual_cash',5,'Cobros menos aportes por año calendario dentro de la ventana suministrada.', 'gross_contributions_receipts_net_cash_operating_cash_and_conditional_CoC'),
        field('R19','CoC anual condicional','ratio','annual_cash_receipts','annual_coc',5,'Sólo cobros operativos / base anual positiva declarada; sin base queda pendiente.'),
        field('R20','Retorno personal','personal','personal_investor_return','direct',None,'Pendiente de términos de reparto aplicables; no inferir proporcionalidad LP/JV.'),
        field('R21','Aportes no recuperados al corte','risk','risk_observations/cash_shortfall_at_horizon','direct',8,'Observación de caja al horizonte; no capital remanente ni pérdida final.'),
        field('R22','Pico de financiación del equity','risk','risk_observations/peak_cumulative_net_equity_funding_at_date_close','direct',8,'Pico al cierre de fechas; no acredita liquidez intradía.'),
        field('R23','Dependencia del cobro de venta','ratio','risk_observations/sale_share_of_distributions','direct',8,'Cobro de venta / cobros totales bajo el caso suministrado.'),
    ]


def field_observation(payload,spec,spans):
    story = payload['current_project_return_story']
    if story is None:
        return dict(field_id=spec['field_id'],state='withheld_current_projection',value=None,
                    resolved_source_pointers=[],pdf_manifest_spans=[])
    path = spec['source_pointer']
    source = resolve_pointer(payload,path)
    pointers = [path]
    prefixes = [path]
    selector = spec['selector']
    if spec['quantity_kind'] == 'cash' and path.endswith('/dated_events'):
        events = [event for event in source if event['category'] == selector]
        total_path = STORY+'/cash_by_category/'+selector
        total = resolve_pointer(payload,total_path)
        value = dict(total=total,events=events)
        pointers += [total_path]
        prefixes = [path+'/'+str(i) for i,event in enumerate(source) if event['category'] == selector]
        if not events and selector in ('net_refinance_distribution','refinance_cash_in'):
            require(fraction(total) == 0, 'no-refinance route must retain explicit zero totals')
            state = 'explicit_zero_in_supplied_no_refinance_route'
            prefixes = [STORY+'/cash_by_category']
        else:
            state = 'computed_synthetic_cash'
    elif spec['quantity_kind'] == 'stock':
        value = [{key:row[key] for key in ('as_of_date',selector,'currency','basis_ref','source_ref')} for row in source] or None
        state = 'pending_stock_source_missing' if value is None else 'declared_stock_not_derived'
    elif selector == 'irr':
        value = dict(annual_roots=source,selected_IRR=story['selected_IRR'],periodic_selection=story['periodic_irr']['selected_rate'])
        pointers += [STORY+'/selected_IRR',STORY+'/periodic_irr/selected_rate']
        state = 'intervals_preserved_no_point_selected'
    elif selector == 'annual_cash':
        keys = ('calendar_cash_receipt_year','gross_contributions','gross_distributions','net_equity_cash','operating_distributions_only','operating_year_coverage_financially_verified')
        value = [{key:row[key] for key in keys} for row in source]
        state = 'computed_for_declared_window_not_verified_full_operating_year'
    elif selector == 'annual_coc':
        keys = ('calendar_cash_receipt_year','operating_distributions_only','declared_capital_base','conditional_coc','blocker')
        value = [{key:row[key] for key in keys} for row in source]
        state = 'pending_annual_base_missing' if all(row['conditional_coc'] is None for row in source) else 'conditional_supplied_basis_only'
    else:
        value = source
        state = 'pending_personal_allocation' if spec['quantity_kind'] == 'personal' and value is None else 'available_synthetic'
    matched = [row for row in spans if any(ref == prefix or ref.startswith(prefix+'/') or prefix.startswith(ref+'/')
                for ref in row['result_pointers'] for prefix in prefixes)]
    return dict(field_id=spec['field_id'],state=state,value=value,resolved_source_pointers=pointers,
                pdf_manifest_spans=matched)


def consistency_checks(story):
    events = story['dated_events']; norm = story['normalized_story']; annual = story['annual_cash_receipts']
    a = fraction(story['gross_contributions']); d = fraction(story['gross_distributions']); profit = fraction(story['net_cash_profit'])
    total = lambda rows:sum((fraction(row['amount']) for row in rows),Fraction(0))
    category = {key:fraction(value) for key,value in story['cash_by_category'].items()}
    reference = fraction(norm['reference_amount']); basis = fraction(norm['basis_amount']); scale = fraction(norm['scale_factor'])
    conditions = [
        ('gross_contributions',total([e for e in events if e['kind']=='contribution']) == a),
        ('gross_receipts',total([e for e in events if e['kind']=='distribution']) == d),
        ('net_cash_result',d-a == profit),
        ('gross_equity_multiple',a>0 and d/a == fraction(story['equity_multiple'])),
        ('contribution_categories',sum(category[k] for k in ('initial_capital','additional_capital','refinance_cash_in')) == a),
        ('distribution_categories',sum(category[k] for k in ('operating_distribution','net_sale_distribution','net_refinance_distribution','other_distribution')) == d),
        ('annual_contributions',sum(fraction(row['gross_contributions']) for row in annual) == a),
        ('annual_receipts',sum(fraction(row['gross_distributions']) for row in annual) == d),
        ('annual_net_result',sum(fraction(row['net_equity_cash']) for row in annual) == profit),
        ('annual_row_identity',all(fraction(row['gross_distributions'])-fraction(row['gross_contributions']) == fraction(row['net_equity_cash']) for row in annual)),
        ('explicit_normalization_basis',total([e for e in events if e['event_id'] in norm['basis_event_ids']]) == basis),
        ('explicit_positive_normalization',reference>0 and basis>0 and reference/basis == scale),
        ('normalized_contributions',fraction(norm['total_contributions']) == a*scale),
        ('normalized_receipts',fraction(norm['total_distributions']) == d*scale),
        ('normalized_net_cash',fraction(norm['net_cash_profit']) == profit*scale),
        ('normalized_events_not_netted',len(events)==len(norm['events']) and all(fraction(n['amount']) == fraction(e['amount'])*scale and all(n[k]==e[k] for k in ('event_id','date','kind','category')) for e,n in zip(events,norm['events']))),
        ('zero_events_preserved',sum(fraction(e['amount'])==0 for e in events) == 3),
        ('IRR_point_not_selected',story['selected_IRR'] is None and story['periodic_irr']['selected_rate'] is None),
        ('absent_stock_not_cash_shortfall',story['capital_snapshots']==[] and story['personal_investor_return'] is None),
        ('annual_base_not_defaulted',all(row['declared_capital_base'] is None and row['conditional_coc'] is None for row in annual)),
        ('risk_cash_shortfall',fraction(story['risk_observations']['cash_shortfall_at_horizon']) == max(a-d,0)),
    ]
    require(len(conditions)==21 and all(value for name,value in conditions),'investor return consistency check failed')
    return [name for name,value in conditions]


def build_snapshot():
    from miniuw_foundation.policy_renewal_case import assemble_policy_renewal_case
    from miniuw_foundation.investor_onepage import render_investor_onepage
    from pypdf import PdfReader
    sources = [local_file(ROOT,path).read_bytes() for path in CASES]
    expired = next(row for row in definitions(sources[0]) if row['scenario_id']=='D06-04')
    sources.append(probe_source(sources[0],expired))
    specs = output_definitions(); flow = json.loads(local_file(ROOT,FLOW).read_bytes())
    for spec in specs: require(type(resolve_pointer(flow,spec['requirement_pointer'])) is str,'exact requirement locator must resolve')
    rows = []
    for index,raw in enumerate(sources):
        run = assemble_policy_renewal_case(raw); p = run.payload
        report = render_investor_onepage(raw,run); reader = PdfReader(io.BytesIO(report.pdf_bytes))
        require(len(reader.pages)==1,'one-page investor PDF required')
        text = reader.pages[0].extract_text(); spans = report.manifest['display_spans']
        require(all(row['text'] in text for row in spans),'investor PDF manifest text missing')
        if index == 0:
            require(local_file(ROOT,EXAMPLE+'MiniUW_v1_Resumen.pdf').read_bytes() == report.pdf_bytes,
                    'published T96 example PDF differs from source replay')
            require(local_file(ROOT,EXAMPLE+'report-manifest.json').read_bytes() == (report.manifest_json+'\n').encode(),
                    'published T96 example manifest differs')
            require(local_file(ROOT,EXAMPLE+'results.json').read_bytes() == (run.payload_json+'\n').encode(),
                    'published T96 example result differs from unchanged T94 run')
            audit = json.loads(local_file(ROOT,EXAMPLE+'audit.json').read_bytes())
            expected_audit = dict(component='T96',status='passed_scoped_presentation_check',source_path=CASES[0],
                input_sha256=sha(raw),run_sha256=run.sha256,pdf_sha256=sha(report.pdf_bytes),manifest_sha256=report.manifest_sha256,
                page_count=1,display_spans_verified=len(spans),annual_cash_scope='supplied_window_not_verified_full_operating_year',
                underlying_financial_pipeline_changed=False,independent_financial_audit=False,
                financial_publication_authorized=False,decision='PENDING',deployment_enabled=False,real_decisions_enabled=False)
            require(audit == expected_audit,'published T96 example audit differs from actual replay')
        require(p['decision']=='PENDING' and p['real_decisions_enabled'] is False and p['financial_publication_authorized'] is False,'operational release must remain blocked')
        current = p['current_project_return_story'] is not None
        require(current == (index<2),'supplied investor example currentness differs')
        if current:
            refs = {ref for span in spans for ref in span['result_pointers']}
            require(all(STORY+'/'+key in refs for key in ('currency','equity_level','cash_horizon')),
                    'current investor context must have explicit report pointers')
            for year_index,year in enumerate(p['current_project_return_story']['annual_cash_receipts']):
                require(all(STORY+'/annual_cash_receipts/'+str(year_index)+'/'+key in refs for key in
                            ('gross_contributions','gross_distributions','net_equity_cash','operating_distributions_only','conditional_coc')),
                        'complete supplied-window annual cash report pointers required')
                require(year['operating_year_coverage_financially_verified'] is False,
                        'supplied partial cash window cannot certify a full operating year')
        fields = [field_observation(p,spec,spans) for spec in specs]
        checks = consistency_checks(p['current_project_return_story']) if current else []
        if not current: require(all(row['value'] is None for row in fields),'blocked investor current values leaked')
        rows.append(dict(case_id=('baseline','renewal_12','expired_policy')[index],
                         input_file=CASES[index] if index<2 else CASES[0],
                         source_sha256=sha(raw),input_mutation=None if index<2 else expired,
                         run_sha256=run.sha256,decision=p['decision'],current_projection_available=current,
                         fields=fields,consistency_checks=checks,blockers=p['blockers'],
                         pdf=dict(page_count=1,pdf_sha256=sha(report.pdf_bytes),manifest_sha256=report.manifest_sha256)))
    functions = [source_function(ROOT,module,symbol) for module,symbol in [
        ('investor_returns','produce_investor_returns'),('staged_lifecycle_returns','assemble_staged_lifecycle_returns'),
        ('cash_risk','summarize_cash_risk'),('policy_renewal_case','assemble_policy_renewal_case'),
        ('policy_renewal_artifacts','render_policy_renewal_report'),('investor_onepage','render_investor_onepage')]]
    paths = {row['path'] for row in functions} | {FLOW,'AGENTS.md','src/miniuw_foundation/v1_report.py',
        'tools/check_investor_output_D07.py','tools/check_dependency_structure_D05.py','tools/check_blocking_structure_D06.py',
        DIRECTORY+'MiniUW_Bloqueos_D06.json',DIRECTORY+'MiniUW_Estructura_Vigente_D04.json','docs/technical-implementation-T96.md',*CASES}
    paths |= {EXAMPLE+name for name in ('MiniUW_v1_Resumen.pdf','report-manifest.json','results.json','audit.json')}
    return dict(snapshot_id='D07',technical_baseline='T96',financial_pipeline_baseline='T95',registered_technical_unit_tests=1355,
                scope='Investor-output structure, exact synthetic cash identities and existing PDF span traceability; not financial acceptance',
                output_fields=specs,cases=rows,function_locations=functions,
                source_versions=[dict(path=path,sha256=sha(local_file(ROOT,path).read_bytes())) for path in sorted(paths)],
                annual_net_cash_report_complete_for_supplied_window=True,personal_return_verified=False,
                capital_snapshots_derived=False,annual_CoC_financial_basis_adopted=False,
                original_field_runtime_mappings_pending=54,financial_model_complete=False,
                professional_review_authenticated=False,independent_financial_audit=False,
                deployment_enabled=False,real_decisions_enabled=False)


def flat_csv(snapshot):
    stream = io.StringIO(newline='')
    keys = ['field_id','label','quantity_kind','requirement_location','runtime_source_pointer','selector','definition',
            'baseline_state','baseline_exact_value','renewal_12_state','expired_policy_state','baseline_pdf_spans','presentation_scope']
    writer = csv.DictWriter(stream,fieldnames=keys); writer.writeheader()
    for index,spec in enumerate(snapshot['output_fields']):
        observed = [case['fields'][index] for case in snapshot['cases']]
        writer.writerow(dict(field_id=spec['field_id'],label=spec['label'],quantity_kind=spec['quantity_kind'],
            requirement_location=spec['requirement_document']+'#'+spec['requirement_pointer'],runtime_source_pointer=spec['source_pointer'],
            selector=spec['selector'],definition=spec['definition'],baseline_state=observed[0]['state'],
            baseline_exact_value=json.dumps(observed[0]['value'],ensure_ascii=False,sort_keys=True,separators=(',',':')),
            renewal_12_state=observed[1]['state'],expired_policy_state=observed[2]['state'],
            baseline_pdf_spans=len(observed[0]['pdf_manifest_spans']),presentation_scope=spec['presentation_scope']))
    return stream.getvalue().encode()


def validate(snapshot,expected):
    require(snapshot==expected,'D07 output contract/values/locators/PDF observations differ from actual replay')


def faults(snapshot,expected):
    tests = [
        ('personal_return_invented',lambda p:p['cases'][0]['fields'][19].update(value={'guaranteed_receipts':'10'})),
        ('cash_shortfall_as_capital',lambda p:p['cases'][0]['fields'][15].update(value='622')),
        ('invented_full_operating_year_verification',lambda p:p['cases'][0]['fields'][17]['value'][0].update(operating_year_coverage_financially_verified=True)),
        ('blocked_cash_exposed',lambda p:p['cases'][2]['fields'][10].update(value='778')),
        ('missing_output_field',lambda p:p['output_fields'].pop()),
        ('unsupported_release',lambda p:p.update(real_decisions_enabled=True)),
    ]
    rejected = []
    for name,mutate in tests:
        altered = copy.deepcopy(snapshot); mutate(altered)
        try: validate(altered,expected)
        except PackageError: rejected.append(name)
        else: raise PackageError('altered investor-output evidence accepted: '+name)
    return rejected


def validation_record(snapshot,rejected):
    return dict(snapshot='D07',status='passed_scoped_investor_output_and_replay_check',
                checker_sha256=sha(Path(__file__).read_bytes()),output_fields_checked=len(snapshot['output_fields']),
                cases_replayed=3,pdfs_replayed_and_text_checked=3,
                published_example_artifacts_verified=4,
                exact_consistency_checks_per_current_case=21,current_cases_checked=2,blocked_cases_checked=1,
                source_hashes_checked=len(snapshot['source_versions']),negative_structural_cases_rejected=rejected,
                annual_net_cash_report_complete_for_supplied_window=True,personal_return_verified=False,capital_stock_derived=False,
                financial_validation_performed=False,professional_review_authenticated=False,
                independent_financial_audit=False,deployment_enabled=False,real_decisions_enabled=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--emit-snapshot',action='store_true'); parser.add_argument('--emit-record',action='store_true'); args = parser.parse_args()
    try:
        expected = build_snapshot()
        if args.emit_snapshot: print(json.dumps(expected,ensure_ascii=False,indent=2))
        else:
            snapshot = json.loads(local_file(ROOT,SNAPSHOT).read_bytes()); validate(snapshot,expected)
            require(local_file(ROOT,CSV).read_bytes()==flat_csv(snapshot),'D07 CSV differs')
            result = validation_record(snapshot,faults(snapshot,expected))
            if not args.emit_record: require(json.loads(local_file(ROOT,RECORD).read_bytes())==result,'D07 validation record differs')
            print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError,IndexError,StopIteration) as error:
        print(json.dumps(dict(status='failed',reason=str(error),financial_validation_performed=False))); sys.exit(1)
