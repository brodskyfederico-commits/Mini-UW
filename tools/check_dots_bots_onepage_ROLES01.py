"""Check the one-page Spanish summary against the preserved Dot/bot contract."""
from pathlib import Path
import hashlib
import json
import sys
from pypdf import PdfReader
from check_reference_package import require,local_file,PackageError

ROOT=Path(__file__).resolve().parents[1]
DIRECTORY='docs/review/'
normalize=lambda value:' '.join(value.split())
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def verify():
    source=json.loads(local_file(ROOT,DIRECTORY+'dots-bots-onepage-source-ROLES01.json').read_bytes())
    record=json.loads(local_file(ROOT,DIRECTORY+'dots-bots-onepage-validation-ROLES01.json').read_bytes())
    require(source['document_id']=='ROLES01','supported role summary required')
    contract_raw=local_file(ROOT,source['source_path']).read_bytes();contract=json.loads(contract_raw)
    require(sha(contract_raw)==source['source_sha256'],'role source contract hash differs')
    require([r['dot_id']for r in source['dots']]==[r['dot_id']for r in contract['dots']],'exact seven Dot IDs required')
    require([r['bot_id']for r in source['bots']]==[r['bot_id']for r in contract['bots']],'exact seventeen bot IDs required')
    dots={r['dot_id']:r for r in contract['dots']};bots={r['bot_id']:r for r in contract['bots']}
    require(all(r['bot_ids']==dots[r['dot_id']]['bot_ids']for r in source['dots']),'Dot/bot membership differs')
    require(all(r['dot_id']==bots[r['bot_id']]['dot_id']for r in source['bots']),'bot owner Dot differs')
    require(contract['external_actions_enabled']is False and contract['real_decisions_enabled']is False,'role release guard changed')
    for original in contract['sources']:
        require(sha(local_file(ROOT,original['path']).read_bytes())==original['sha256'],'original role source changed')
    require(record['pdf_path']==DIRECTORY+'MiniUW_Dots_y_Bots_1_pagina_ROLES01.pdf','fixed role PDF location required')
    raw=local_file(ROOT,record['pdf_path']).read_bytes();require(sha(raw)==record['pdf_sha256'],'role PDF hash differs')
    reader=PdfReader(local_file(ROOT,record['pdf_path']));require(len(reader.pages)==1,'exact one-page role summary required')
    text=normalize(reader.pages[0].extract_text())
    for row in source['dots']:
        require(all(normalize(row[key])in text for key in ('dot_id','name','purpose','status')),'Dot content missing from PDF')
    for row in source['bots']:
        require(all(normalize(row[key])in text for key in ('bot_id','name','purpose')),'bot content missing from PDF')
    require('ningún agente está desplegado'in text and 'PENDIENTE'in text,'planned-scope/pending disclaimer missing')
    require(record['status']=='passed_scoped_document_check'and record['pages']==1 and record['dots']==7 and record['bots']==17,'role verification counts differ')
    require(all(record[k]is True for k in ('source_mapping_verified','text_extracted','span_bounds_verified')),'creation validation missing')
    require(record['external_agents_deployed']is False and record['financial_model_complete']is False,'unsupported role deployment/financial claim')
    return dict(document_id='ROLES01',status='passed_scoped_role_document_check',pages=1,dots=7,bots=17,
                pdf_sha256=sha(raw),contract_mapping_verified=True,PDF_text_verified=True,
                creation_bounds_check_preserved=True,agents_deployed=False,financial_model_complete=False)


if __name__=='__main__':
    try:print(json.dumps(verify(),ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError,PackageError)as error:
        print(json.dumps(dict(status='failed',reason=str(error))));sys.exit(1)
