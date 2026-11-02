"""Explicit review branches; no actual reviewer, acceptance or active-case change."""
import copy,json
from pathlib import Path
from miniuw_foundation.screening import simulate_screening
from miniuw_foundation.review_proposals import evaluate_review_proposal
from miniuw_foundation.archive import EvidenceArchive


def main():
    root=Path(__file__).resolve().parents[1]
    base=(root/'templates/synthetic-screening-band-case.json').read_bytes()
    screen=simulate_screening(base)
    template=json.loads((root/'templates/synthetic-screening-review-proposal.json').read_bytes())
    results={}
    with EvidenceArchive(':memory:') as archive:
        for name,numerator in [('explicit_pass_proposal','55'),('explicit_fail_proposal','35'),('still_in_band','46')]:
            proposal=copy.deepcopy(template)
            proposal['proposal_id']='SYNTHETIC-'+name
            proposal['new_case_id']='SYNTHETIC-candidate-'+name
            proposal['new_run_id']='SYNTHETIC-run-'+name
            proposal['patches'][0]['proposed_after']['numerator']=numerator
            raw=json.dumps(proposal).encode()
            run=evaluate_review_proposal(base,screen,raw)
            restored=archive.load_review_proposal(archive.save_review_proposal(base,screen,raw,run))
            assert restored.run==run and restored.base_run==screen
            results[name]={key:run.payload[key] for key in ['candidate_simulation_result','decision',
                'proposal_accepted','professional_review_authenticated','automatic_variable_optimization']}
    assert simulate_screening(base)==screen
    return {'purpose':'synthetic_development_only','original_simulation_result':screen.payload['simulation_result'],
        'original_preserved':True,'proposals':results,'deployment_enabled':False}


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
