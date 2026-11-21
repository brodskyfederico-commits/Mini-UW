"""Fresh source-first delivery of the nine-block monthly review page."""
from pathlib import Path
from argparse import ArgumentParser
from hashlib import sha256
import json
from worksheet_intake_D198 import read_source_directory,assemble,register
from worksheet_monthly_analysis_D276 import request
from worksheet_decision_page_D275 import deliver
from worksheet_review_controls_D275 import empty_roles
from miniuw_worksheet_v1 import encoded,read_package,CURRENT_REVISION_FILE
from check_monthly_oracle_D276 import verify

ROOT=Path(__file__).resolve().parents[1]


def run(output):
 output=Path(output);output.mkdir(parents=True,exist_ok=False);fixture=ROOT/'templates/golden_case_v2';sources=read_source_directory(fixture,include_reference=True);settings=json.loads((fixture/'settings.json').read_bytes());package=output/'package';assemble(settings,register(sources,'SYNTHETIC-D276-REVIEW-CURRENT'),sources,package);saved=read_package(package);current=output/'current_revision.json';current.write_bytes(saved[CURRENT_REVISION_FILE]);manifest=output/'analysis_request.json';manifest.write_bytes(encoded(request(saved['case.json'],sources)));print('Baseline source packet created',flush=True)
 result=json.loads(saved['results.json']);proof=verify(settings,sources,result);assert proof['observations']==json.loads((fixture/'expected_financials.json').read_bytes());(output/'oracle.json').write_bytes(encoded(proof));print('Independent literal-source oracle passed',flush=True)
 receipt=deliver(package,output/'MiniUW_Resultado_Una_Pagina_D276.pdf',current,manifest,empty_roles());(output/'delivery.json').write_bytes(encoded(receipt));analysis=receipt['view']['analyses'];(output/'analysis.json').write_bytes(encoded(analysis));print('Nine-block current source-replayed PDF delivered',flush=True);return receipt

if __name__=='__main__':
 p=ArgumentParser();p.add_argument('output',type=Path);run(p.parse_args().output)
