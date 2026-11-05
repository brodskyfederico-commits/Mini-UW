"""Read-only nominal settlement timing checks; original full-window guard preserved."""
from fractions import Fraction as F
from pathlib import Path
import argparse,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from miniuw_foundation.drafts import ValidationError,canonical
from miniuw_foundation.debt_service import _fraction,rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.expense_schedule import produce_expense_schedule,parse_expense_schedule
from miniuw_foundation.deferred_insurance_settlement import reconcile_deferred_insurance_settlement
from miniuw_foundation.deferred_insurance_artifacts import (audit_deferred_insurance_directory,read_deferred_insurance_artifacts,
    recover_deferred_insurance_directory,write_deferred_insurance_artifacts)

EXAMPLE=ROOT/'docs/review/miniuw-v1-deferred-insurance-example'
RECORD=ROOT/'docs/review/deferred-insurance-validation-T106.json'
q=lambda value:rational(F(value))
encoded=lambda p:(canonical(p)+'\n').encode()


def require(value,message):
    if not value:raise ValidationError(message)


def verify():
    audit=audit_deferred_insurance_directory(EXAMPLE);files=read_deferred_insurance_artifacts(EXAMPLE);main=recover_deferred_insurance_directory(EXAMPLE)
    require(files['settlement-results.json']==(main.payload_json+'\n').encode(),'saved nominal settlement result differs from source-first recovery')
    fixture=json.loads((ROOT/'docs/review/insurance-settlement-fixture-generation-T106.json').read_bytes());original=(ROOT/fixture['original_control']).read_bytes()
    require(sha(original)==fixture['original_control_sha256'],'original T90 source changed')
    require([r['label']for r in fixture['cases']]==['control','deferred','late','prepaid','on-cut','missing','zero'],'seven explicit nominal plans required')
    # Independent known-money oracles: before/on/after cash, nominal tail, past-due/non-prepaid tails, before/on/after dues.
    oracle={'control':(20,0,0,0,0,0,20,0,0),'deferred':(15,0,5,5,0,5,15,0,5),
        'late':(15,0,5,5,5,0,20,0,0),'prepaid':(20,0,0,0,0,0,15,0,5),
        'on-cut':(15,5,0,5,0,5,15,5,0),'zero':(0,0,0,0,0,0,0,0,0)}
    cases=[];by_label={}
    for row in fixture['cases']:
        raw=(ROOT/row['path']).read_bytes();require(sha(raw)==row['sha256'],'declared settlement source bytes changed')
        run=main if raw==files['settlement-source.json']else reconcile_deferred_insurance_settlement(raw);p=run.payload;totals=p['totals']
        require((p['state'],p['integration_state'],p['blockers'],totals)==(row['state'],row['integration_state'],row['blockers'],row['totals']), 'declared source plan did not reproduce')
        for key in('nominal_tail_is_approved_legal_liability','actual_bank_payments_verified','source_or_due_date_authority_verified',
            'insurance_coverage_sufficiency_verified','tax_or_accounting_policy_adopted','penalties_or_prepayment_rights_verified',
            'case_or_cash_or_return_modified','full_case_financial_integration_completed','automatic_funding_or_buyer_transfer_created',
            'new_external_PDF_created','financial_publication_authorized','deployment_enabled','real_decisions_enabled'):
            require(p[key]is False,'plan became an authority or automatic financial action: '+key)
        require(p['decision']=='PENDING'and p['currency']=='USD'and p['cutoff_date']=='2027-07-01'and not p['cutoff_includes_same_date_events'], 'scope/currency/cut/decision convention changed')
        if row['label']=='missing':
            require(totals is None and p['terminal_settlement_source_required']is None,'unknown payment became zero or no terminal exposure')
            require(all(r['allocated_expense']is None for r in p['allocations'])and
                all(r['nominal_not_settled_before_cut']is None for r in p['due_installments']),'partial derived amounts survived missing data')
        else:
            values=(*[totals['cash_by_cut_bucket'][k]for k in('before_cut','on_cut','after_cut')],totals['nominal_not_settled_before_cut'],
                totals['due_before_cut_not_settled'],totals['not_due_before_cut_not_prepaid'],
                *[totals['due_by_cut_bucket'][k]for k in('before_cut','on_cut','after_cut')])
            require(values==tuple(q(v)for v in oracle[row['label']]),'independent due/cash/cut/tail oracle differs')
            total=0 if row['label']=='zero'else 20
            require(totals['allocated_expense']==totals['nominal_installments']==totals['planned_payments']==q(total), 'nominal/accrual/whole-plan conservation fails')
            require(totals['fraction_sum']==q(1),'supplied fractional inventory changed')
            require(p['terminal_settlement_source_required']==(oracle[row['label']][3]>0),'terminal source gate differs')
            for index,due in enumerate(p['due_installments']):
                amounts=[p['planned_payments'][i]['amount']for i in due['payment_indices']]
                require(sum((_fraction(a)for a in amounts),F(0))==_fraction(due['amount']),'per-installment payment conservation fails')
                require(due['source_pointer']=='/due_installments/'+str(index),'installment source locator changed')
            require(sorted(i for d in p['due_installments']for i in d['payment_indices'])==list(range(len(p['planned_payments']))), 'payment inventory omitted, duplicated or implicitly generated')
        by_label[row['label']]=p
        cases.append(dict(label=row['label'],source_sha256=sha(raw),run_sha256=run.sha256,state=p['state'],integration_state=p['integration_state'],
            terminal_settlement_source_required=p['terminal_settlement_source_required'],totals=totals,blockers=p['blockers']))
    legacy=produce_expense_schedule(original).payload
    require(legacy['totals']['expense']==by_label['control']['totals']['allocated_expense']and
        legacy['totals']['installments']==by_label['control']['totals']['nominal_installments'],'full-window control changed prior expense')
    require([a['allocated_expense']for a in legacy['allocations']]==[a['allocated_expense']for a in by_label['control']['allocations']], 'prior period expense allocations changed')
    # Same supplied deferred dues remain unsupported by the old strict T90 profile.
    old=json.loads(original);old['installments']=by_label['deferred']['source']['due_installments'];guard=produce_expense_schedule(encoded(old)).payload
    require(guard['totals']is None and any('outside_half_open_service_window'in b for b in guard['blockers']), 'old full-window guard was silently loosened')
    try:parse_expense_schedule(files['settlement-source.json'])
    except ValidationError:pass
    else:raise ValidationError('new schema incorrectly accepted by old full-window parser')
    with tempfile.TemporaryDirectory()as td:
        root=Path(td)/'blocked';missing=next(r for r in fixture['cases']if r['label']=='missing')
        write_deferred_insurance_artifacts((ROOT/missing['path']).read_bytes(),root);blocked=recover_deferred_insurance_directory(root)
        require(blocked.payload['totals']is None and blocked.payload['terminal_settlement_source_required']is None,'source-first recovery restored unknown settlement money')
    paths=('src/miniuw_foundation/deferred_insurance_settlement.py','src/miniuw_foundation/deferred_insurance_artifacts.py',
        'src/miniuw_foundation/expense_schedule.py','tools/deferred_insurance_miniuw_v1.py','tools/check_deferred_insurance_T106.py',
        'docs/technical-implementation-T106.md','docs/technical-implementation-T90-T92.md','docs/review/insurance-settlement-fixture-generation-T106.json')
    return dict(component='T106',status='passed_source_first_nominal_settlement_and_independent_cut_oracles',files_verified=audit['files_verified'],
        fixture_sources_checked=7,cases=cases,run_sha256=main.sha256,original_T90_source_sha256=sha(original),
        original_full_window_expense_preserved=True,original_off_window_guard_preserved=True,dues_not_treated_as_payments=True,
        nominal_tail_not_discarded=True,blocked_source_directory_recovery_verified=True,
        source_versions=[dict(path=path,sha256=sha((ROOT/path).read_bytes()))for path in paths],
        full_case_financial_integration_completed=False,new_external_PDF_created=False,actual_bank_payments_verified=False,
        actual_legal_liability_approved=False,original_semantic_mappings_pending=54,financial_publication_authorized=False,
        deployment_enabled=False,real_decisions_enabled=False,decision='PENDING')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--emit-record',action='store_true');args=parser.parse_args()
    try:
        result=verify()
        if not args.emit_record:require(json.loads(RECORD.read_bytes())==result,'stored settlement verification differs')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except(ValueError,OSError,KeyError,TypeError)as error:
        print(json.dumps(dict(status='failed',reason=str(error),financial_validation_performed=False)));sys.exit(1)
