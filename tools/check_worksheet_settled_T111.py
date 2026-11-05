"""Read-only source-first worksheet/claims/settled return and one-page evidence."""
from pathlib import Path
from fractions import Fraction as F
from io import BytesIO
import argparse,base64,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from pypdf import PdfReader
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.debt_service import rational
from miniuw_foundation.phased_settled_output import assemble_phased_settled_output
from miniuw_foundation.worksheet_settled_output import assemble_worksheet_settled_output,required_sources
from miniuw_foundation.worksheet_settled_report import render_worksheet_settled_output
from miniuw_foundation.worksheet_settled_artifacts import recover_worksheet_settled_directory,validate_report
from check_settled_lifecycle_T108 import certificate

RECORD=ROOT/'docs/review/worksheet-settled-validation-T111.json';q=lambda n:rational(F(n))


def require(value,message):
    if not value:raise ValidationError(message)


def verify():
    fixtures=json.loads((ROOT/'docs/review/worksheet-settled-fixtures-T111.json').read_bytes());cases=[];certificates=[]
    require(sha((ROOT/fixtures['original_workbook']).read_bytes())==fixtures['original_sha256'],'original supplied worksheet changed')
    require([r['label']for r in fixtures['cases']]==['matched','zero-conflict','formula','expired','parent-expired','zero-matched','twelve'],'seven explicit worksheet/source cases required')
    for row in fixtures['cases']:
        raw=(ROOT/row['path']).read_bytes();source=json.loads(raw);run=assemble_worksheet_settled_output(raw);p=run.payload;report=render_worksheet_settled_output(raw,run);audit=validate_report(raw,run,report);m=report.manifest
        require(sha(raw)==row['source_sha256']and run.sha256==row['run_sha256']and sha(report.pdf_bytes)==row['pdf_sha256']and p['state']==row['state'],'worksheet source/result/PDF did not reproduce')
        require(p['required_sources']==required_sources(raw)and p['source_requirements_checked']==59,'complete parent/claim/XLSX/binding/definition engine source gate differs')
        check=p['worksheet_reconciliation'];claims=json.loads(source['claims_source_utf8']);require(len(check['rows'])==55 and [r['field_id']for r in check['rows']]==[r['field_id']for r in claims['original_inputs']],'complete original55-field inventory differs')
        for i,field in enumerate(check['rows']):
            require(field['worksheet_locator']=='xlsx:sheet:Inputs:cell:'+field['cell']and field['claim_pointer']=='/claims_source_utf8::json/original_inputs/'+str(i)+'/value'and field['worksheet_source_sha256']==sha(base64.b64decode(source['workbook_base64'],validate=True)),'exact cell/hash/claim pointer missing')
            require(field['financial_semantics_verified']is False,'representation agreement became financial mapping')
        for key in ('worksheet_values_adopted','projection_computed_from_55_claims','worksheet_financial_semantics_completed','parent_result_used_as_current_fallback','original_sheet_adapter_for_this_profile_implemented','financial_model_complete','financial_publication_authorized','source_authority_verified','professional_review_authenticated','deployment_enabled','real_decisions_enabled'):require(p[key]is False,'synthetic claim gate became financial adoption: '+key)
        require(p['decision']=='PENDING'and p['personal_investor_return']is None and p['original_semantic_mappings_pending']==54 and all(c['threshold']is None and c['state']=='PENDING'for c in p['criterion_slots']),'financial/personal threshold policy adopted')
        if row['label']in('matched','zero-matched','twelve'):
            parent=assemble_phased_settled_output(source['phased_settled_source_utf8'].encode()).payload
            for k,v in parent.items():
                if k.startswith('current_'):require(p[k]==v,'worksheet gate changed parent cash/root/risk: '+k)
            twelve=row['label']=='twelve';s=p['current_project_return_story'];expected=dict(gross_contributions=q(1400),gross_distributions=q(776 if twelve else 778),net_cash_profit=q(-624 if twelve else -622),equity_multiple=q(F(97,175)if twelve else F(389,700)))
            require(all(s[k]==v for k,v in expected.items()),'independent cash return oracle differs')
            require([r['net']for r in s['dated_net_flows']]==[q(v)for v in[-1000,-400,0,0,0,100,0,0,100,576 if twelve else 578]],'complete dated equity cash including zeros differs')
            require(p['current_settlement_summary']['settlement_cash']==q(5)and p['current_operating_totals']['closing_free_cash_claim']==q(211 if twelve else 213)and p['current_rental_totals']['effective_rent']==q(88),'retained cash/settlement/rent oracle differs')
            require(check['counts']==dict(MATCHED_REPRESENTATION=2 if row['label']=='zero-matched'else 1,MISSING_BOTH=53 if row['label']=='zero-matched'else 54),'declared representation/missing count differs')
            require(m['annual_years']==[2026,2027]and m['annual_rows_omitted']==0 and sorted(i for g in m['event_groups']for i in g['event_indices'])==list(range(8))and sum(g['zero_event_count']for g in m['event_groups'])==3,'gross/zero/annual cash omitted or duplicated')
            certificates.append(dict(label=row['label'],**certificate(s)))
        else:
            require(all(v is None for k,v in p.items()if k.startswith('current_'))and m['all_current_money_withheld']and m['event_groups']==[]and m['annual_years']==[],'blocked worksheet/source restored parent money')
            if row['label']=='zero-conflict':require(any(r['state']=='CONFLICT'and r['decoded_representation']==q(0)and r['claim']['value']is None for r in check['rows']),'explicit zero missing conflict not retained')
            if row['label']=='formula':require(any(r['worksheet_cell']['cached_value']=='2'and r['decoded_representation']is None for r in check['rows']),'formula cache wrongly adopted')
            if row['label']=='parent-expired':require(p['worksheet_gate_open']and json.loads(p['registry_run']['payload_json'])['state']=='current_synthetic_evidence','parent/child expiry controls not separate')
        if row['label']in('matched','zero-conflict','expired'):
            saved,rr=recover_worksheet_settled_directory(ROOT/('docs/review/miniuw-v1-worksheet-settled-'+row['label']+'-example'));require(saved==run and rr==report,'six-file saved output differs from source-first recovery')
        reader=PdfReader(BytesIO(report.pdf_bytes));require(len(reader.pages)==1 and tuple(float(v)for v in reader.pages[0].mediabox)==(0.0,0.0,792.0,612.0),'exact one-page profile required')
        text=reader.pages[0].extract_text();require(all(span['text']in text for span in m['display_spans'])and'Resultado T111 SHA256: '+run.sha256 in text,'complete PDF span/result identity missing')
        cases.append(dict(label=row['label'],source_sha256=sha(raw),run_sha256=run.sha256,pdf_sha256=sha(report.pdf_bytes),state=p['state'],sources=59,fields_checked=55,worksheet_gate_open=p['worksheet_gate_open'],counts=check['counts'],all_current_money_withheld=m['all_current_money_withheld'],page_count=audit['page_count']))
    paths=['src/miniuw_foundation/'+n+'.py'for n in ('worksheet_settled_output','worksheet_settled_report','worksheet_settled_artifacts')]+['tools/worksheet_settled_miniuw_v1.py','tools/check_worksheet_settled_T111.py','tests/test_worksheet_settled_output.py','docs/technical-implementation-T111.md','docs/review/worksheet-settled-fixtures-T111.json']
    return dict(component='T111',status='passed_original55_claims_source_gate_full_settled_cash_one_page_and_source_first_recovery',source_cases_checked=7,fields_per_case=55,source_requirements_per_case=59,saved_output_directories_checked=3,files_per_directory=6,PDF_pages_per_output=1,cases=cases,independent_IRR_certificates=certificates,all_parent_current_cash_stock_risk_and_roots_preserved=True,all_current_money_withheld_on_any_blocker=True,source_versions=[dict(path=p,sha256=sha((ROOT/p).read_bytes()))for p in paths],original_semantic_mappings_pending=54,worksheet_values_adopted=False,projection_computed_from_55_claims=False,financial_field_mapping_completed=False,source_authority_verified=False,professional_review_authenticated=False,personal_return_verified=False,visual_independent_financial_audit_performed=False,financial_model_complete=False,financial_publication_authorized=False,deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--emit-record',action='store_true');args=parser.parse_args()
    try:
        result=verify()
        if not args.emit_record:require(json.loads(RECORD.read_bytes())==result,'stored T111 verification differs')
        print(json.dumps(result,indent=2))
    except(ValueError,OSError,TypeError,KeyError)as error:
        print(json.dumps(dict(status='failed',reason=str(error),financial_validation_performed=False)));sys.exit(1)
