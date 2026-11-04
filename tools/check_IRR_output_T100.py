"""Read-only source-first IRR package replay and independent sparse certificate."""
from fractions import Fraction as F
from io import BytesIO
from pathlib import Path
import argparse,json,sys
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.debt_service import _fraction
from miniuw_foundation.irr_checked_output import assemble_irr_checked_output
from miniuw_foundation.irr_checked_artifacts import audit_irr_checked_directory,recover_irr_checked_bundle
from miniuw_foundation.scheduled_expense_artifacts import read_artifacts
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.v1_report import annual_irr

EXAMPLE=ROOT/'docs/review/miniuw-v1-IRR-checked-example'
RECORD=ROOT/'docs/review/IRR-output-validation-T100.json'


def verify():
    audit=audit_irr_checked_directory(EXAMPLE);files=read_artifacts(EXAMPLE)
    recovered=recover_irr_checked_bundle(files['execution-evidence.json']);run=recovered.run;p=run.payload;s=p['current_project_return_story']
    if (recovered.case_raw!=files['case.json']or(run.payload_json+'\n').encode()!=files['results.json']
        or recovered.report.pdf_bytes!=files['MiniUW_v1_Resumen.pdf']
        or(recovered.report.manifest_json+'\n').encode()!=files['report-manifest.json']):
        raise ValidationError('IRR output differs from source-first portable recovery')
    if recovered.case_raw!=(ROOT/'templates/miniuw-v1-long-window-case.json').read_bytes():
        raise ValidationError('unchanged T99 long source required for before/after comparison')
    before=run.parent_run.payload['current_project_return_story'];e=p['irr_recalculation'];r=s['periodic_irr']
    for key in s:
        if key not in ('periodic_irr','annual_irr_roots','upstream_story_blockers')and s[key]!=before[key]:
            raise ValidationError('unrelated financial current-view field changed: '+key)
    if (before['periodic_irr']['root_classification']!='arithmetic_budget_exhausted'
        or r['status']!='complete_synthetic'or r['distinct_positive_discount_roots']!=1
        or r['coefficient_bit_limit']!=4096 or r['operation_budget']!=e['parameters']['operation_budget']
        or r['arithmetic_operations']>r['operation_budget']):
        raise ValidationError('same-budget numerical before/after result differs')
    if (s['selected_IRR']is not None or next(m for m in p['metrics']if m['metric_id']=='IRR')['value']is not None
        or any(m['criterion']['source_ref']is not None for m in p['metrics'])or p['decision']!='PENDING'):
        raise ValidationError('point rate, criteria or financial decision introduced')
    coefficients={i:_fraction(row['net'],1300)for i,row in enumerate(e['dated_net_flows'])if _fraction(row['net'],1300)}
    if len(e['dated_net_flows'])!=65 or coefficients!={0:F(-1000),56:F(-400),60:F(100),63:F(100),64:F(578)}:
        raise ValidationError('explicit long-case sparse polynomial differs')
    # Independent certificate: P(x)/x^56 is strictly increasing for x>0.
    if any(c*(i-56)<=0 for i,c in coefficients.items()if i!=56):
        raise ValidationError('termwise positive derivative certificate failed')
    root=r['roots'][0];iv=root['discount_factor_interval'];a,b=F(iv['lower']),F(iv['upper'])
    evaluate=lambda x:sum(c*x**i for i,c in coefficients.items())
    if not(0<a<b and evaluate(a)<0<=evaluate(b))or root['multiplicity']!=1:
        raise ValidationError('exact original-polynomial endpoint certificate failed')
    annual=s['annual_irr_roots'][0]['annual_rate_interval']
    if (_fraction(annual['lower'],1300)!=b**-12-1 or _fraction(annual['upper'],1300)!=a**-12-1
        or annual['lower_closed']is not True or annual['upper_closed']is not False):
        raise ValidationError('independent annual discount-factor transformation differs')
    pages=PdfReader(BytesIO(recovered.report.pdf_bytes));text=pages.pages[0].extract_text();m=recovered.report.manifest
    if (len(pages.pages)!=1 or any(row['text']not in text for row in m['display_spans'])
        or 'IRR anual: '+annual_irr(s['annual_irr_roots'])not in text
        or 'Resultado T100 SHA256: '+run.sha256 not in text
        or 'Capital declarado: Pendiente'not in text):
        raise ValidationError('one-page current IRR/capital/result evidence missing')
    generation=json.loads((ROOT/'docs/review/IRR-fixture-generation-T100.json').read_bytes());cases=[]
    if len(generation['cases'])!=2:raise ValidationError('two declared numerical pending fixtures required')
    for record in generation['cases']:
        source=(ROOT/record['path']).read_bytes()
        if sha(source)!=record['sha256']:raise ValidationError('pending fixture bytes changed')
        current=assemble_irr_checked_output(source).payload;story=current['current_project_return_story']
        if current['irr_output_state']!='PENDING'or story['annual_irr_roots']:
            raise ValidationError('pending numerical controls gained an annual rate')
        if current['irr_recalculation']['parameters']!=record['parameters']:
            raise ValidationError('source numerical controls changed')
        cases.append(dict(path=record['path'],sha256=record['sha256'],state=current['irr_output_state'],periodic_status=story['periodic_irr']['status']))
    return dict(component='T100',status='passed_same_source_primitive_IRR_and_independent_sparse_certificate',
        files_verified=audit['files_verified'],page_count=1,source_requirements=len(p['required_source_bindings']),
        pending_fixture_revisions_checked=2,prior_numerical_status=before['periodic_irr']['status'],
        current_numerical_status=r['status'],distinct_positive_discount_roots=1,root_multiplicity=1,
        operation_budget=r['operation_budget'],arithmetic_operations=r['arithmetic_operations'],coefficient_bit_limit=4096,
        independent_sparse_endpoint_signs_verified=True,independent_unique_root_derivative_verified=True,
        independent_annual_discount_transformation_verified=True,periodic_interval_width_source=e['parameters']['max_periodic_rate_interval_width'],
        annual_interval=annual,displayed_annual_IRR=annual_irr(s['annual_irr_roots']),gross_cash_unchanged=True,
        source_unchanged_from_T99=True,pending_capital_preserved=True,point_rate_selected=False,
        pending_cases=cases,source_sha256=sha(files['case.json']),run_sha256=run.sha256,
        parent_capital_run_sha256=run.parent_run.sha256,pdf_sha256=sha(files['MiniUW_v1_Resumen.pdf']),
        manifest_sha256=recovered.report.manifest_sha256,bundle_sha256=sha(files['execution-evidence.json']),
        source_versions=[dict(path=path,sha256=sha((ROOT/path).read_bytes()))for path in
            ('src/miniuw_foundation/primitive_periodic_returns.py','src/miniuw_foundation/irr_checked_output.py',
             'src/miniuw_foundation/irr_checked_artifacts.py','src/miniuw_foundation/long_horizon_report.py',
             'src/miniuw_foundation/investor_returns.py','src/miniuw_foundation/capital_checked_output.py',
             'tools/irr_miniuw_v1.py','tools/check_IRR_output_T100.py','docs/technical-implementation-T100.md',
             'docs/review/IRR-fixture-generation-T100.json')],financial_policy_adopted=False,personal_return_verified=False,
        financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--emit-record',action='store_true');args=parser.parse_args()
    try:
        result=verify()
        if not args.emit_record and json.loads(RECORD.read_bytes())!=result:raise ValidationError('stored IRR validation differs')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError)as error:
        print(json.dumps(dict(status='failed',reason=str(error),financial_validation_performed=False)));sys.exit(1)
