"""Read-only two-source revision replay, exact deltas and blocked-candidate recovery."""
from fractions import Fraction as F
from io import BytesIO
from pathlib import Path
import argparse,json,sys
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.debt_service import _fraction
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.irr_interval_artifacts import recover_irr_interval_bundle
from miniuw_foundation.irr_revision_review import compare_irr_revisions,_from_verified_pair
from miniuw_foundation.irr_review_artifacts import (audit_review_directory,read_review_artifacts,
    export_review_bundle,recover_review_bundle)

EXAMPLE=ROOT/'docs/review/miniuw-v1-IRR-revision-review-example'
RECORD=ROOT/'docs/review/IRR-revision-review-validation-T102.json'


def require(condition,message):
    if not condition:raise ValidationError(message)


def verify():
    audit=audit_review_directory(EXAMPLE);files=read_review_artifacts(EXAMPLE)
    before=recover_irr_interval_bundle(files['reference-evidence.json'])
    after=recover_irr_interval_bundle(files['candidate-evidence.json'])
    main=_from_verified_pair(before.case_raw,after.case_raw,files['comparison-spec.json'],before.run,after.run)
    require(files['revision-review.json']==(main.payload_json+'\n').encode(),'saved comparison differs from full replay')
    require(after.report.pdf_bytes==files['candidate-MiniUW_v1_Resumen.pdf'],'PDF is not exclusively candidate output')
    pages=PdfReader(BytesIO(after.report.pdf_bytes));text=pages.pages[0].extract_text()
    require(len(pages.pages)==1 and 'Decision: PENDIENTE'in text and 'cumple regla (sim.)'in text,
        'candidate PDF lost its single-condition/global-pending distinction')
    require(after.run.sha256 in text,'candidate run linkage missing from PDF')
    generation=json.loads((ROOT/'docs/review/revision-fixture-generation-T102.json').read_bytes())
    require([r['label']for r in generation['cases']]==['criteria','renewal','expired'],'three explicit revisions required')
    rows=[]
    for record in generation['cases']:
        args=tuple((ROOT/record[k]).read_bytes()for k in('reference','candidate','spec'))
        require(all(sha(raw)==record[k+'_sha256']for raw,k in zip(args,('reference','candidate','spec'))),'declared source/spec bytes changed')
        if record['label']=='criteria':
            require(args==(before.case_raw,after.case_raw,files['comparison-spec.json']),'example is not the declared criteria revision')
            run=main
        else:run=compare_irr_revisions(*args)
        p=run.payload;b,a=p['reference_snapshot'],p['candidate_snapshot'];d=p['projection_deltas']
        require(p['state']==record['state']and d==record['projection_deltas'],'declared revision result differs')
        require(len(p['decoded_source_changes'])==record['decoded_source_changes'],'complete source change inventory differs')
        require(b['IRR_interval_condition']['row_state']==record['reference_condition']and
            a['IRR_interval_condition']['row_state']==record['candidate_condition'],'condition change differs')
        for key in('candidate_adopted','active_revision_changed','candidate_generated','reference_snapshot_is_candidate_fallback',
            'source_or_rule_automatically_adjusted','isolated_variable_causality_claimed','professional_review_authenticated',
            'financial_publication_authorized','deployment_enabled','real_decisions_enabled'):
            require(p[key]is False,'automatic action or authority introduced: '+key)
        require(p['decision']==b['decision']==a['decision']=='PENDING','a condition became a real deal decision')
        require(p['annual_IRR']['selected_rate']is None and p['annual_IRR']['rate_delta']is None,'an IRR point was selected')
        if record['label']=='criteria':
            require(b['current_project_return_story']==a['current_project_return_story']and not p['financial_story_changes'],
                'criterion revision changed cash or returns')
            require(all(_fraction(v)==0 for v in d.values()),'criterion change has an economic delta')
            prefix='/scheduled_case_utf8::json/base_case_utf8::json/criteria/8/'
            changed={r['pointer']:r for r in p['criterion_source_changes']}
            # Independent literal rule checks, not just equality with a stored report.
            require(prefix+'pass_condition/threshold'in changed,'nested criterion threshold locator missing')
            c=changed[prefix+'pass_condition/threshold']
            require(_fraction(c['before'])==0and _fraction(c['after'])==F(-1,5),
                'declared synthetic IRR thresholds differ from the supplied rules')
            require(any('/registry_utf8::json/'in r['pointer']for r in p['decoded_source_changes']),
                'source/evidence changes were hidden behind criterion-only attribution')
        elif record['label']=='renewal':
            require({k:_fraction(v)for k,v in d.items()}==dict(gross_contributions=F(0),gross_distributions=F(-2),
                net_cash_profit=F(-2),equity_multiple=F(-1,700)),'independent exact renewal deltas differ')
            require(_fraction(b['current_project_return_story']['gross_distributions'])==778 and
                _fraction(a['current_project_return_story']['gross_distributions'])==776,'supplied aggregate receipts differ')
            sale=next(r for r in p['event_deltas']if r['category']=='net_sale_distribution')
            require(_fraction(sale['reference_amount'])==578 and _fraction(sale['candidate_amount'])==576 and
                _fraction(sale['delta'])==-2,'sale receipts/delta differ')
            require(_fraction(p['normalization_comparison']['deltas']['total_distributions'])==F(-1,70),
                'explicit project scaling delta differs')
        else:
            require(b['current_project_return_story']is not None and a['current_project_return_story']is None and
                d is None and p['event_deltas']is None,'expired candidate borrowed reference figures')
            portable=export_review_bundle(*args,run);recovered=recover_review_bundle(portable)
            require(recovered.run==run and(recovered.reference_raw,recovered.candidate_raw,recovered.spec_raw)==args,
                'blocked portable two-source recovery differs')
            require(recovered.run.payload['candidate_snapshot']['current_project_return_story']is None,
                'portable recovery restored unavailable candidate money')
            blocked_pages=PdfReader(BytesIO(recovered.candidate_report.pdf_bytes))
            require(len(blocked_pages.pages)==1 and 'Decision: PENDIENTE'in blocked_pages.pages[0].extract_text(),
                'blocked candidate PDF is not pending')
        rows.append(dict(label=record['label'],reference_sha256=sha(args[0]),candidate_sha256=sha(args[1]),
            spec_sha256=sha(args[2]),run_sha256=run.sha256,state=p['state'],
            reference_condition=b['IRR_interval_condition']['row_state'],candidate_condition=a['IRR_interval_condition']['row_state'],
            decoded_source_changes=len(p['decoded_source_changes']),criterion_source_changes=len(p['criterion_source_changes']),
            financial_story_changes=len(p['financial_story_changes']),projection_deltas=d,comparison_blockers=p['comparison_blockers']))
    paths=('src/miniuw_foundation/irr_revision_review.py','src/miniuw_foundation/irr_review_artifacts.py',
        'src/miniuw_foundation/v1_revision.py','src/miniuw_foundation/irr_interval_output.py',
        'src/miniuw_foundation/irr_interval_artifacts.py','tools/irr_review_miniuw_v1.py',
        'tools/check_IRR_revision_review_T102.py','docs/technical-implementation-T102.md',
        'docs/review/revision-fixture-generation-T102.json')
    return dict(component='T102',status='passed_source_first_revision_review_and_independent_exact_deltas',
        files_verified=audit['files_verified'],page_count=1,fixture_pairs_checked=3,conditions=rows,
        run_sha256=main.sha256,pdf_sha256=sha(after.report.pdf_bytes),manifest_sha256=sha(files['package.json']),
        source_versions=[dict(path=p,sha256=sha((ROOT/p).read_bytes()))for p in paths],
        full_source_changes_preserved=True,criterion_only_cash_invariant=True,independent_renewal_deltas_verified=True,
        expired_candidate_portable_recovery_verified=True,reference_fallback_used=False,candidate_adopted=False,
        active_revision_changed=False,IRR_point_selected=False,financial_publication_authorized=False,
        deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--emit-record',action='store_true');args=parser.parse_args()
    try:
        result=verify()
        if not args.emit_record:require(json.loads(RECORD.read_bytes())==result,'stored revision review verification differs')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except(ValueError,OSError,KeyError,TypeError)as error:
        print(json.dumps(dict(status='failed',reason=str(error),financial_validation_performed=False)));sys.exit(1)
