"""Reproduce the three D268 incomplete IRRs without changing financial sources."""
from argparse import ArgumentParser
from copy import deepcopy
import json
from pathlib import Path

from check_worksheet_scenario_program_D268 import (settings, drivers, make_packet, sources_for,
    packet_hash, reference, independently_verify)
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded, read_package, CURRENT_REVISION_FILE, verify_package, deliver_package
from worksheet_intake_D198 import assemble, register, source_inventory
from worksheet_irr_certificate_D270 import PROFILE, RULES, implementation_sha256


def method_config():
    return dict(profile=PROFILE,rules=deepcopy(RULES),algorithm_sha256=implementation_sha256(),
                source_ref="SYNTHETIC-D270-explicit-exact-numerical-definition")


def execute(spec,sources,output,revision):
    output.mkdir(parents=True,exist_ok=False)
    (output/'settings.json').write_bytes(encoded(spec))
    for key,filename in source_inventory(sources).items():
        (output/filename).write_bytes(sources[key])
    receipt=assemble(spec,register(sources,revision),sources,output/'package')
    saved=read_package(output/'package')
    result=json.loads(saved['results.json'])
    (output/'receipt.json').write_bytes(encoded(receipt))
    audit=verify_package(output/'package',current_revision_raw=saved[CURRENT_REVISION_FILE])
    assert audit['vigencia']=='VIGENTE' and audit['critical_evidence']['status']=='PASSED'
    return result,saved,audit


def source_base(output):
    spec=settings();initial=sources_for(spec,output/'seed')
    return make_packet(spec,initial,'baseline',[],drivers(),output/'origin')


def source_case(base,base_sources,key,output):
    parent={name:raw for name,raw in base_sources.items() if name!='independent_reference_raw'}
    original,sources=make_packet(base,parent,key,[key],drivers(),output)
    frozen=json.loads((Path(__file__).resolve().parents[1]/'templates/synthetic-scenario-program-D268.json').read_bytes())
    assert packet_hash(original,sources)==frozen['variants'][key]['packet_sha256'], 'D268 financial source drift'
    return original,sources


def certified_sources(original,sources):
    spec=deepcopy(original);spec['rent_inputs']['irr_certificate']=method_config()
    changed=dict(sources)
    # Financial documents retain their actual D268 revisions. Only the analytical
    # definition/reference and designated evaluation revision change.
    reference_sources={name:raw for name,raw in sources.items() if name!='independent_reference_raw'}
    inventory=reference(spec,reference_sources)
    original_inventory=json.loads(sources['independent_reference_raw'])
    if 'regulated_rents' in original_inventory:
        inventory['regulated_rents']=deepcopy(original_inventory['regulated_rents'])
    changed['independent_reference_raw']=encoded(inventory)
    return spec,changed


def verify_joint(output):
    from check_worksheet_regulated_rent_D269 import settings as rent_settings, make_sources, independently_verify as verify_rent
    output.mkdir(parents=True,exist_ok=False)
    original,sources=make_sources(rent_settings(),output)
    fixture=json.loads((Path(__file__).resolve().parents[1]/'templates/synthetic-regulated-rent-D269.json').read_bytes())
    assert original['rent_inputs']['regulated_rent']==fixture['regulated_rent']
    spec,updated=certified_sources(original,sources)
    result,saved,audit=execute(spec,updated,output/'current','SYNTHETIC-D270-joint-AMI-certificate')
    assert result['critical_evidence_review']['critical_fields']==130
    checks=verify_rent(spec,updated,result)
    previous=json.loads((Path(__file__).resolve().parents[1]/'docs/review/MiniUW_Validacion_D269.json').read_bytes())
    hashes={}
    for name in ('Base','Downside'):
        hashes[name]={}
        for route,view in [('with_refi',result['scenarios'][name]),('without_refi',result['scenarios'][name]['horizon_without_refinance'])]:
            digest=sha(encoded(view['cash_per_usd_10']))
            assert digest==previous['comparisons'][name]['routes'][route]['dated_cash_sha256']
            hashes[name][route]=digest
    proof=dict(profile=spec['schema'],current_audit=audit,independent_checks=checks,
        cash_sha256=hashes,same_dated_cash_as_D269=True,critical_fields=130,
        case_sha256=sha(saved['case.json']),results_sha256=sha(saved['results.json']))
    (output/'validation.json').write_bytes(encoded(proof))
    return proof


def verify(output):
    output.mkdir(parents=True,exist_ok=False)
    fixture=json.loads((Path(__file__).resolve().parents[1]/'templates/synthetic-irr-certificate-D270.json').read_bytes())
    assert fixture['usage']=='synthetic_test_only_no_financial_defaults'
    assert fixture['irr_certificate']==method_config(), 'Versioned numerical definition drift'
    base,base_sources=source_base(output)
    cases={}
    for key in ('18','28','29'):
        original,sources=source_case(base,base_sources,key,output/('source-'+key))
        before,saved_before,old_audit=execute(original,sources,output/('legacy-'+key),'SYNTHETIC-D270-'+key+'-legacy')
        spec,updated=certified_sources(original,sources)
        result,saved,audit=execute(spec,updated,output/('current-'+key),'SYNTHETIC-D270-'+key+'-certificate')
        assert before['screening']['irr_by_scenario']['Downside']['annual_enclosure'] is None
        assert 'IRR_incomplete_root_inventory_current_intervals_withheld' in before['screening']['irr_by_scenario']['Downside']['blockers']
        assert original['rules']==spec['rules'] and original['criteria_revision']==spec['criteria_revision']
        assert all(sources[name]==updated[name] for name in sources if name!='independent_reference_raw')
        cash_hashes={};irrs={}
        for name in ('Base','Downside'):
            old,new=before['scenarios'][name],result['scenarios'][name]
            assert old['noi_by_period']==new['noi_by_period']
            assert old['construction_financing']==new['construction_financing'] and old['capacity']==new['capacity']
            cash_hashes[name]={};irrs[name]={}
            for route,prior,current in [('with_refi',old,new),('without_refi',old['horizon_without_refinance'],new['horizon_without_refinance'])]:
                assert prior['cash_per_usd_10']==current['cash_per_usd_10'], (key,name,route)
                cash_hashes[name][route]=sha(encoded(current['cash_per_usd_10']))
                irr=result['screening']['irr_by_scenario'][name] if route=='with_refi' else current['irr']
                assert irr['state']=='checked_synthetic' and irr['annual_enclosure'] is not None and not irr['blockers']
                assert irr['complete_root_inventory']['positive_roots']==1 and irr['complete_root_inventory']['complete']
                irrs[name][route]=irr
        checks=independently_verify(spec,updated,result)
        cases[key]=dict(old_case_sha256=sha(saved_before['case.json']),new_case_sha256=sha(saved['case.json']),
            before_audit=old_audit,current_audit=audit,cash_sha256=cash_hashes,irr=irrs,independent_checks=checks,
            same_financial_source_bytes=True,same_criteria=True,same_dated_cash_bytes=True,
            old_simulation=before['simulation_result'],new_simulation=result['simulation_result'])
    package=output/'current-28/package'
    current=output/'Current.json';current.write_bytes((package/CURRENT_REVISION_FILE).read_bytes())
    destination=output/'MiniUW_TIR_Verificada_D270.pdf'
    delivery=deliver_package(package,destination,current)
    joint=verify_joint(output/'joint-AMI')
    report=dict(milestone='D270',status='passed',profile=PROFILE,algorithm_sha256=implementation_sha256(),
        cases=cases,joint_AMI=joint,financial_routes_reconciled=28,current_certified_routes=16,
        financial_inputs_changed=False,criteria_changed=False,dated_cash_changed=False,
        delivery=delivery,pdf_sha256=sha(destination.read_bytes()),real_decision='PENDING',historical_return='PENDING',
        personal_return_without_terms='PENDING',deployment_enabled=False,real_decisions_enabled=False,
        all_33_policies_certified=False,
        scope='Opt-in exact quarterly root inventory; multiple, missing, unproved or out-of-budget cases remain PENDING')
    (output/'validation.json').write_bytes(encoded(report))
    return report


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    args=parser.parse_args();result=verify(args.output)
    print(json.dumps({key:result[key] for key in ('status','current_certified_routes','financial_inputs_changed','dated_cash_changed')}))


if __name__=='__main__':main()
