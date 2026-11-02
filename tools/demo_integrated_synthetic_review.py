"""Synthetic source -> proposed revision -> durable replay -> lifecycle -> one-page preview."""
from pathlib import Path
import argparse,copy,hashlib,json,tempfile
from miniuw_foundation.scenario_threshold_rehearsal import simulate_scenario_thresholds
from miniuw_foundation.scenario_review import SCHEMA,evaluate_scenario_proposal
from miniuw_foundation.archive import EvidenceArchive
from miniuw_foundation.proposal_queue import ProposalQueue
from miniuw_foundation.synthetic_onepager import render_synthetic_onepager


def proposal(doc,base,run,ident,amount):
    p=json.loads(base)
    return {'schema':SCHEMA,'proposal_id':ident,'document_sha256':hashlib.sha256(doc).hexdigest(),
        'base_case_sha256':hashlib.sha256(base).hexdigest(),'base_run_sha256':run.sha256,
        'new_case_id':ident+'-case','new_run_id':ident+'-run','author_label':'SYNTHETIC reviewer label only',
        'reason':'Explicit fictional metric revision','evidence_refs':['SYNTHETIC-evidence:revision'],
        'patches':[{'metric_id':'YoC','scenario_id':'Base','expected_before':p['metric_values'][0]['value'],
            'proposed_after':amount,'reason':'Fictional replacement observation, not automatic optimization'}],'status':'proposal_only'}


def main(preview_output=None):
    root=Path(__file__).resolve().parents[1]
    doc=(root/'sources/originals/38b78d40013b__Estandares_de_underwriting_Lorena.docx').read_bytes()
    p=json.loads((root/'templates/synthetic-documented-threshold-base.json').read_bytes())
    p['case_id']='SYNTHETIC-integration-original';p['run_id']='SYNTHETIC-integration-original-run'
    p['metric_values'][0]['value']={'numerator':'6','denominator':'100'}
    base=json.dumps(p).encode();base_run=simulate_scenario_thresholds(doc,base)
    first_raw=json.dumps(proposal(doc,base,base_run,'SYNTHETIC-integrated-first',{'numerator':'7','denominator':'100'})).encode()
    first=evaluate_scenario_proposal(doc,base,base_run,first_raw)
    second_raw=json.dumps(proposal(doc,first.candidate_raw,first.candidate_run,'SYNTHETIC-integrated-second',{'numerator':'5','denominator':'100'})).encode()
    second=evaluate_scenario_proposal(doc,first.candidate_raw,first.candidate_run,second_raw)
    full=(root/'templates/synthetic-documented-threshold-full.json').read_bytes();full_run=simulate_scenario_thresholds(doc,full)
    preview=render_synthetic_onepager(doc,full,full_run)
    with tempfile.TemporaryDirectory()as temporary:
        archive_path=Path(temporary)/'evidence.sqlite3';queue_path=Path(temporary)/'queue.sqlite3'
        with EvidenceArchive(archive_path)as archive,ProposalQueue(queue_path)as queue:
            first_key=archive.save_scenario_review(doc,base,base_run,first_raw,first)
            second_key=archive.save_scenario_review(doc,first.candidate_raw,first.candidate_run,second_raw,second)
            queue.record(archive,first_key,operation_id='SYNTHETIC-record',expected_revision=0,actor_label='SYNTHETIC operator',reason='Record explicit proposal')
            queue.supersede(archive,first.payload['proposal_id'],second_key,operation_id='SYNTHETIC-supersede',expected_revision=1,actor_label='SYNTHETIC operator',reason='Replace with exact descendant')
            queue.withdraw(second.payload['proposal_id'],operation_id='SYNTHETIC-withdraw',expected_revision=2,actor_label='SYNTHETIC operator',reason='Demonstrate reversible lifecycle without approval')
        with EvidenceArchive(archive_path)as archive,ProposalQueue(queue_path)as queue:
            assert archive.load_scenario_review(first_key).run==first
            assert archive.load_scenario_review(second_key).run==second
            snapshot=queue.snapshot();events=[r.payload['outcome']for r in queue.history()]
            assert snapshot['revision']==3 and len(events)==3
            queue.verify_entry(archive,first.payload['proposal_id']);queue.verify_entry(archive,second.payload['proposal_id'])
    assert simulate_scenario_thresholds(doc,base)==base_run
    if preview_output is not None:
        Path(preview_output).write_bytes(preview.pdf_bytes)
        Path(str(preview_output)+'.manifest.json').write_text(preview.manifest_json+'\n')
    return {'purpose':'synthetic_integrated_components_only','original_preserved':True,
        'original_simulation_result':base_run.payload['simulation_result'],
        'first_candidate_simulation_result':first.payload['candidate_simulation_result'],
        'second_candidate_simulation_result':second.payload['candidate_simulation_result'],
        'source_and_proposal_chain_replayed_after_reopen':True,'queue':snapshot,'events':events,
        'full_scenario_simulation_result':full_run.payload['simulation_result'],'full_scenario_blockers':full_run.payload['simulation_blockers'],
        'preview_manifest':preview.manifest,'runtime_databases_retained':False,'proposal_accepted':False,
        'decision':'PENDING','professional_review_authenticated':False,'production_authorized':False,'full_miniuw_completed':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--preview-output');args=parser.parse_args()
    print(json.dumps(main(args.preview_output),ensure_ascii=False,indent=2))
