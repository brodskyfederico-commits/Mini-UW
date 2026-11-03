"""T87 validate the declared functional contracts, without starting external bots."""
from pathlib import Path
import hashlib
import json
from .drafts import ValidationError

PATH=Path(__file__).resolve().parents[2]/'docs/miniuw-v1-dot-bot-contracts.json'
ENGINE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def load_contracts():
    raw=PATH.read_bytes();p=json.loads(raw)
    if p['schema']!='miniuw.synthetic-v1-dot-bot-contracts.v1' or p['external_actions_enabled']is not False or p['real_decisions_enabled']is not False:
        raise ValidationError('non-operational v1 bot contracts required')
    if [d['dot_id']for d in p['dots']]!=['D'+str(i).zfill(2)for i in range(1,8)]or [b['bot_id']for b in p['bots']]!=['B'+str(i).zfill(2)for i in range(1,18)]:
        raise ValidationError('complete seven Dot/seventeen bot inventory required')
    bots={b['bot_id']:b for b in p['bots']};members=[]
    for d in p['dots']:
        if not all(d[k]for k in ('inputs','outputs','blockers','status')):raise ValidationError('complete Dot contract required')
        for bid in d['bot_ids']:
            if bid not in bots or bots[bid]['dot_id']!=d['dot_id']:raise ValidationError('Dot membership mismatch')
            members.append(bid)
    if len(members)!=17 or set(members)!=set(bots):raise ValidationError('each bot must belong to exactly one Dot')
    for b in p['bots']:
        if not all(b[k]for k in ('inputs','outputs','blockers','status'))or b['external_actions_enabled']is not False or b['real_decisions_enabled']is not False:
            raise ValidationError('complete non-operational bot contract required')
        if any(dep not in bots for dep in b['depends_on']):raise ValidationError('unknown bot dependency')
    done=set()
    def visit(bid,stack):
        if bid in stack:raise ValidationError('cyclic bot dependency')
        if bid in done:return
        for dep in bots[bid]['depends_on']:visit(dep,stack|{bid})
        done.add(bid)
    for bid in bots:visit(bid,set())
    for bid in ('B03','B05','B06','B07','B08','B09','B10','B11'):
        if bots[bid]['status']!='contract_only_pending':raise ValidationError('unimplemented extraction/official role cannot be claimed operational')
    for source in p['sources']:
        path=PATH.parents[1]/source['path']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=source['sha256']:raise ValidationError('historical role source changed')
    return p,hashlib.sha256(raw).hexdigest()
