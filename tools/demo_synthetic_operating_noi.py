"""Explicit synthetic accrual inputs and conditional max-tax equation only."""
import copy,json,tempfile
from pathlib import Path
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.archive import EvidenceArchive


def main():
    root=Path(__file__).resolve().parents[1];base=json.loads((root/'templates/synthetic-operating-noi.json').read_bytes())
    cases={'proxy_branch':base}
    p=copy.deepcopy(base);p['tax_floor']['value']={'numerator':'300','denominator':'1'};p['context']['run_id']='SYNTHETIC-floor-run';cases['floor_branch']=p
    p=copy.deepcopy(base);p['tax_coefficient']['value']=None;p['context']['run_id']='SYNTHETIC-missing-k';cases['missing_coefficient']=p
    output={}
    with tempfile.TemporaryDirectory()as temporary:
        path=Path(temporary)/'noi.sqlite3';keys={}
        with EvidenceArchive(path)as archive:
            for name,p in cases.items():
                raw=json.dumps(p).encode();run=produce_operating_noi(raw);keys[name]=archive.save_operating_noi(raw,run)
                output[name]={k:run.payload[k]for k in ['operating_before_tax','noi','property_tax','tax_branch','equation_residual','blockers','decision','tax_policy_adopted']}
        with EvidenceArchive(path)as archive:
            for name,key in keys.items():assert archive.load_operating_noi(key).run.payload['noi']==output[name]['noi']
    return {'purpose':'conditional_synthetic_NOI_only','cases':output,'reopened_archive_replayed':True,'runtime_database_retained':False,'tax_law_verified':False,'financial_module_closed':False,'production_authorized':False}


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
