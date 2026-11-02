"""Documented scenario roles with preserved unresolved asking applicability."""
from pathlib import Path
import copy,json
from miniuw_foundation.scenario_threshold_rehearsal import simulate_scenario_thresholds
from miniuw_foundation.archive import EvidenceArchive


def main():
    root=Path(__file__).resolve().parents[1]
    source=(root/'sources/originals/38b78d40013b__Estandares_de_underwriting_Lorena.docx').read_bytes()
    p=json.loads((root/'templates/synthetic-documented-threshold-full.json').read_bytes())
    cases={'source_conditions':p}
    changed=copy.deepcopy(p);changed['case_id']='SYNTHETIC-downside-miss';changed['run_id']='SYNTHETIC-downside-miss-run'
    next(r for r in changed['metric_values']if r['metric_id']=='YoC'and r['scenario_id']=='Downside')['value']={'numerator':'1','denominator':'100'}
    cases['downside_below_pass']=changed
    cases['base_only']=json.loads((root/'templates/synthetic-documented-threshold-base.json').read_bytes())
    results={}
    with EvidenceArchive(':memory:')as archive:
        for name,p in cases.items():
            raw=json.dumps(p).encode();run=simulate_scenario_thresholds(source,raw)
            restored=archive.load_scenario_thresholds(archive.save_scenario_thresholds(source,raw,run))
            assert restored.run==run
            results[name]={k:run.payload[k]for k in ['scope','simulation_result','simulation_blockers','decision','full_miniuw_completed']}
            results[name]['downside_states']=[{'metric_id':r['metric_id'],'state':r['state']}for r in run.payload['comparisons']if r['scenario_id']=='Downside']
    return {'purpose':'synthetic_source_specific_conditions_only','cases':results,'archive_source_case_and_result_replayed':True,'production_authorized':False}


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
