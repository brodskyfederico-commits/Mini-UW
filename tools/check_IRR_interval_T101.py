"""Read-only six-fixture interval-condition replay; no partial deal PASS/FAIL."""
from fractions import Fraction as F
from io import BytesIO
from pathlib import Path
import argparse,json,operator,sys
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.debt_service import _fraction
from miniuw_foundation.irr_interval_output import assemble_irr_interval_output
from miniuw_foundation.irr_interval_artifacts import audit_irr_interval_directory,recover_irr_interval_bundle
from miniuw_foundation.scheduled_expense_artifacts import read_artifacts
from miniuw_foundation.scheduled_expense_case import sha

EXAMPLE=ROOT/'docs/review/miniuw-v1-IRR-interval-example'
RECORD=ROOT/'docs/review/IRR-interval-validation-T101.json'
OPS={'>':operator.gt,'>=':operator.ge,'<':operator.lt,'<=':operator.le}


def independent_relation(interval,condition):
    a,b=_fraction(interval['lower'],1300),_fraction(interval['upper'],1300);t=_fraction(condition['threshold'])
    points={a,b,t,(a+b)/2,(a+t)/2,(t+b)/2}
    samples=[x for x in points if a<x<b or x==a and interval['lower_closed']or x==b and interval['upper_closed']]
    values={OPS[condition['operator']](x,t)for x in samples}
    if not values:raise ValidationError('independent critical-point partition is empty')
    return 'every'if values=={True}else'none'if values=={False}else'mixed'


def verify():
    audit=audit_irr_interval_directory(EXAMPLE);files=read_artifacts(EXAMPLE)
    recovered=recover_irr_interval_bundle(files['execution-evidence.json']);run=recovered.run;p=run.payload
    if(recovered.case_raw!=files['case.json']or(run.payload_json+'\n').encode()!=files['results.json']
        or recovered.report.pdf_bytes!=files['MiniUW_v1_Resumen.pdf']
        or(recovered.report.manifest_json+'\n').encode()!=files['report-manifest.json']):
        raise ValidationError('interval package differs from complete source-first recovery')
    main=p['IRR_interval_comparison']
    if main['row_state']!='BAND'or p['decision']!='PENDING'or p['screening_simulation_result']!='PENDING':
        raise ValidationError('canonical band must stay pending without changing full deal state')
    if not main['professional_review_needed_for_band']or main['variables_automatically_adjusted']:
        raise ValidationError('explicit user band handling changed')
    parent=run.parent_run.payload
    for key in ('current_project_return_story','metrics','screening_run_sha256','screening_simulation_result','capital_visibility','irr_recalculation'):
        if p[key]!=parent[key]:raise ValidationError('parent numerical/cash/criteria state changed: '+key)
    pages=PdfReader(BytesIO(recovered.report.pdf_bytes));text=pages.pages[0].extract_text();m=recovered.report.manifest
    if(len(pages.pages)!=1 or any(row['text']not in text for row in m['display_spans'])
        or 'IRR por intervalo: banda pendiente'not in text or 'Decision: PENDIENTE'not in text or '[fraccion anual]'not in text
        or 'Resultado T101 SHA256: '+run.sha256 not in text):
        raise ValidationError('one-page source/condition/global pending presentation differs')
    generation=json.loads((ROOT/'docs/review/IRR-condition-fixture-generation-T101.json').read_bytes())
    if len(generation['cases'])!=6:raise ValidationError('six explicit synthetic criteria revisions required')
    rows=[];counts={}
    for record in generation['cases']:
        source=(ROOT/record['path']).read_bytes()
        if sha(source)!=record['sha256']:raise ValidationError('criterion fixture bytes changed')
        current=run if source==recovered.case_raw else assemble_irr_interval_output(source)
        view=current.payload;check=view['IRR_interval_comparison'];state=check['row_state']
        if state!=record['expected_row_state']or check['criterion']!=record['criterion']:
            raise ValidationError('declared condition/criterion does not reproduce')
        if view['decision']!='PENDING'or view['screening_simulation_result']!='PENDING'or check['full_deal_result_recomputed']:
            raise ValidationError('single condition became a partial deal PASS/FAIL')
        if view['current_project_return_story']!=current.parent_run.payload['current_project_return_story']:
            raise ValidationError('cash, stocks or roots changed during condition comparison')
        if check['enclosure']is not None and state!='CONFLICT':
            expected={name:independent_relation(check['enclosure'],check['criterion'][name])for name in('pass_condition','fail_condition')}
            if check['relations']!=expected:raise ValidationError('independent critical-point partition disagrees')
        if check['point_rate_selected']or check['precision_automatically_increased']or check['criteria_adopted']:
            raise ValidationError('selection/refinement/adoption introduced')
        counts[state]=counts.get(state,0)+1
        rows.append(dict(path=record['path'],sha256=record['sha256'],row_state=state,relations=check['relations'],
            blockers=check['blockers'],full_deal_state=view['decision']))
    if counts!={'PASS_CONDITION':1,'FAIL_CONDITION':1,'BAND':1,'CONFLICT':1,'PENDING':2}:
        raise ValidationError('condition branch inventory differs')
    blank=(ROOT/'templates/miniuw-v1-long-window-case.json').read_bytes();blank_check=assemble_irr_interval_output(blank).payload['IRR_interval_comparison']
    if blank_check['row_state']!='PENDING'or blank_check['criterion']['source_ref']is not None:
        raise ValidationError('original blank criteria gained a default')
    return dict(component='T101',status='passed_source_first_single_IRR_condition_and_independent_partition',
        files_verified=audit['files_verified'],page_count=1,fixture_revisions_checked=6,condition_counts=counts,
        independent_partition_relations_verified=True,criterion_fraction_unit_labeled=True,original_blank_criterion_preserved=True,
        parent_cash_roots_stocks_criteria_and_screening_unchanged=True,main_band_policy_preserved=True,
        source_requirements=len(p['required_source_bindings']),conditions=rows,point_rate_selected=False,
        full_deal_result_recomputed=False,financial_policy_adopted=False,criteria_adopted=False,
        source_sha256=sha(files['case.json']),run_sha256=run.sha256,parent_IRR_checked_run_sha256=run.parent_run.sha256,
        pdf_sha256=sha(files['MiniUW_v1_Resumen.pdf']),manifest_sha256=recovered.report.manifest_sha256,
        bundle_sha256=sha(files['execution-evidence.json']),
        source_versions=[dict(path=path,sha256=sha((ROOT/path).read_bytes()))for path in
            ('src/miniuw_foundation/irr_interval_output.py','src/miniuw_foundation/irr_interval_artifacts.py',
             'src/miniuw_foundation/irr_checked_output.py','src/miniuw_foundation/screening.py',
             'tools/irr_interval_miniuw_v1.py','tools/check_IRR_interval_T101.py','docs/technical-implementation-T101.md',
             'docs/pending-band-policy-decision.json','docs/review/IRR-condition-fixture-generation-T101.json')],
        financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--emit-record',action='store_true');args=parser.parse_args()
    try:
        result=verify()
        if not args.emit_record and json.loads(RECORD.read_bytes())!=result:raise ValidationError('stored interval condition verification differs')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except(ValueError,OSError,KeyError,TypeError)as error:
        print(json.dumps(dict(status='failed',reason=str(error),financial_validation_performed=False)));sys.exit(1)
