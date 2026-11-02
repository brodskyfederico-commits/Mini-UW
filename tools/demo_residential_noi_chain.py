"""Explicit synthetic rent -> expenses -> conditional NOI -> annual equivalent DSCR."""
from dataclasses import asdict
from pathlib import Path
import hashlib,json,tempfile
from miniuw_foundation.rental_operations import produce_rental_operations
from miniuw_foundation.rental_noi import assemble_rental_noi
from miniuw_foundation.debt_service import produce_debt_service
from miniuw_foundation.operating_dscr import OperatingDscrBinding,calculate_operating_dscr
from miniuw_foundation.archive import EvidenceArchive


def main():
    root=Path(__file__).resolve().parents[1]
    rental=(root/'templates/synthetic-residential-operations.json').read_bytes();spec=(root/'templates/synthetic-residential-noi-assembly.json').read_bytes()
    rr=produce_rental_operations(rental);assembly=assemble_rental_noi(rental,rr,spec)
    if assembly.payload['state']!='computed_synthetic':raise ValueError('synthetic assembly blocked; inspect evidence rather than filling gaps')
    loan=json.loads((root/'templates/synthetic-loan-terms.json').read_bytes());loan['loan_id']='SYNTHETIC-residential-chain-loan'
    loan['context']=assembly.payload['context'];loan['annual_equivalent_ref']=rr.payload['period_ref'];loan_raw=json.dumps(loan).encode();debt=produce_debt_service(loan_raw,())
    binding=OperatingDscrBinding(profile_id='SYNTHETIC-COMPUTED-NOI-ANNUAL-DSCR-v1',definition_revision='SYNTHETIC-residential-NOI-DSCR-chain-v1',
        noi_source_sha256=hashlib.sha256(assembly.compiled_raw).hexdigest(),loan_source_sha256=hashlib.sha256(loan_raw).hexdigest(),noi_run_sha256=assembly.noi_run.sha256,debt_run_sha256=debt.sha256,
        currency=rr.payload['currency'],noi_period_ref=rr.payload['period_ref'],annual_equivalent_ref=loan['annual_equivalent_ref'],declared_annual_noi_basis_ref='SYNTHETIC-explicit-regular-year-basis-not-financially-verified')
    dscr=calculate_operating_dscr(assembly.compiled_raw,assembly.noi_run,loan_raw,(),debt,binding)
    with tempfile.TemporaryDirectory()as temporary:
        path=Path(temporary)/'chain.sqlite3'
        with EvidenceArchive(path)as archive:
            first=archive.save_rental_noi(rental,rr,spec,assembly)
            second=archive.save_operating_dscr(assembly.compiled_raw,assembly.noi_run,loan_raw,(),debt,binding,dscr)
        with EvidenceArchive(path)as archive:
            a=archive.load_rental_noi(first);b=archive.load_operating_dscr(second)
            assert a.run==assembly and b.run==dscr
            assert a.run.noi_run.sha256==b.payload['binding']['noi_run_sha256']
            assert hashlib.sha256(a.run.compiled_raw).hexdigest()==b.payload['noi_source_sha256']
    return {'purpose':'conditional_synthetic_residential_producer_chain','gross_residential_rent':rr.payload['gross_potential_total'],
        'effective_residential_rent':rr.payload['residential_effective_rent'],'operating_expenses_excluding_tax':rr.payload['operating_expenses_excluding_tax'],
        'operating_before_tax':assembly.noi_run.payload['operating_before_tax'],'property_tax':assembly.noi_run.payload['property_tax'],
        'noi':assembly.payload['computed_noi'],'annual_service_equivalent':dscr.payload['annual_service_equivalent'],'dscr':dscr.payload['rational'],
        'binding':asdict(binding),'assembly_bundle_sha256':first,'dscr_bundle_sha256':second,
        'both_stage_bundles_replayed_after_reopen':True,'NOI_source_and_run_links_verified_between_stages':True,
        'runtime_database_retained':False,'financially_validated':False,'tax_policy_adopted':False,
        'cash_collected_or_paid_verified':False,'decision':'PENDING','production_authorized':False}


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
