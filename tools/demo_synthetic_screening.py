"""Side-by-side hypothetical policies, never operational PASS/FAIL."""
import copy,json
from pathlib import Path
from miniuw_foundation.screening import simulate_screening
from miniuw_foundation.archive import EvidenceArchive


def main():
    source=json.loads((Path(__file__).resolve().parents[1]/'templates/synthetic-screening-band-case.json').read_bytes())
    cases={}
    for policy in [None,'pending','fail']:
        p=copy.deepcopy(source);p['hypothetical_band_policy']=policy
        cases['band_requested_'+str(policy)]=p
    p=copy.deepcopy(source);p['metric_values'][1]['value']={'numerator':'5','denominator':'100'};cases['complete_pass']=p
    p=copy.deepcopy(source);p['metric_values'][0]['value']={'numerator':'3','denominator':'100'};p['metric_values'][1]['value']=None;cases['known_fail_plus_missing']=p
    results={}
    with EvidenceArchive(':memory:') as archive:
        for name,p in cases.items():
            raw=json.dumps(p).encode();run=simulate_screening(raw)
            restored=archive.load_screening(archive.save_screening(raw,run))
            results[name]={'simulation_result':restored.run.payload['simulation_result'],
                'comparison_states':[r['state'] for r in restored.run.payload['comparisons']],
                'blockers':restored.run.payload['simulation_blockers'],
                'operational_decision':restored.run.payload['decision'],'criteria_adopted':False,'band_policy_applied':restored.run.payload['band_policy_applied'],
                'professional_review_needed_for_band':restored.run.payload['professional_review_needed_for_band']}
    return {'purpose':'synthetic_screening_policy_preview_only','cases':results,'production_authorized':False}


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
