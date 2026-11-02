"""Replay both synthetic producers before calculating the explicitly scoped ratio."""
from pathlib import Path
import json,tempfile
from miniuw_foundation.operating_noi import produce_operating_noi
from miniuw_foundation.debt_service import produce_debt_service
from miniuw_foundation.operating_dscr import OperatingDscrBinding,calculate_operating_dscr
from miniuw_foundation.archive import EvidenceArchive


def main():
    root=Path(__file__).resolve().parents[1]
    noi=(root/'templates/synthetic-operating-noi.json').read_bytes();loan=(root/'templates/synthetic-operating-dscr-loan.json').read_bytes()
    binding=OperatingDscrBinding(**json.loads((root/'templates/synthetic-operating-dscr-binding.json').read_bytes()))
    nr=produce_operating_noi(noi);dr=produce_debt_service(loan,());run=calculate_operating_dscr(noi,nr,loan,(),dr,binding)
    with tempfile.TemporaryDirectory()as temporary:
        path=Path(temporary)/'bridge.sqlite3'
        with EvidenceArchive(path)as archive:key=archive.save_operating_dscr(noi,nr,loan,(),dr,binding,run)
        with EvidenceArchive(path)as archive:assert archive.load_operating_dscr(key).run==run
    return {'purpose':'computed_conditional_NOI_and_annual_service_only','noi':nr.payload['noi'],'property_tax':nr.payload['property_tax'],
        'annual_service_equivalent':run.payload['annual_service_equivalent'],'dscr':run.payload['rational'],'blockers':run.payload['blockers'],
        'interpretation':run.payload['interpretation_label'],'both_producers_and_bridge_replayed_after_reopen':True,
        'bank_minimum_applied':False,'financially_validated':False,'decision':'PENDING','production_authorized':False}


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
