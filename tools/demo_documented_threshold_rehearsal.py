"""Read the preserved source thresholds and compare fictional metric observations."""
import copy,json
from pathlib import Path
from miniuw_foundation.threshold_rehearsal import rehearse


def main():
    root=Path(__file__).resolve().parents[1]
    source=(root/'sources/originals/38b78d40013b__Estandares_de_underwriting_Lorena.docx').read_bytes()
    base=json.loads((root/'templates/synthetic-documented-threshold-base.json').read_bytes())
    cases={'base_only_pass':base}
    for name,num in [('base_only_fail','50'),('base_only_band','60'),('base_fail_boundary','525')]:
        p=copy.deepcopy(base);p['case_id']='SYNTHETIC-'+name;p['run_id']='SYNTHETIC-run-'+name
        p['metric_values'][0]['value']={'numerator':num,'denominator':'10000'if name=='base_fail_boundary'else'1000'}
        cases[name]=p
    p=copy.deepcopy(cases['base_only_fail']);p['case_id']='SYNTHETIC-fail-plus-missing';p['run_id']='SYNTHETIC-fail-plus-missing-run'
    p['metric_values']=[r for r in p['metric_values']if r['metric_id']!='IRR'];cases['base_fail_plus_missing']=p
    cases['full_source_gaps']=json.loads((root/'templates/synthetic-documented-threshold-full.json').read_bytes())
    return {'purpose':'source_backed_comparator_experiment_only','cases':{name:rehearse(source,json.dumps(case).encode())for name,case in cases.items()},
        'full_miniuw_completed':False,'production_authorized':False}


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
