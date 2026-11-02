"""Strict synthetic JSON adapter; hashes actual bytes, never evaluates formulas."""
import hashlib
import json
from .drafts import RawClaim, ValidationError

SCHEMA = 'miniuw.synthetic-claims.v1'
MAX_BYTES = 1_048_576  # Technical request bound, not a financial input limit.
CLAIM_KEYS = frozenset({'claim_id', 'slot_kind', 'slot_id', 'literal',
    'unit_literal', 'currency_literal', 'period_literal', 'definition_ref'})


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError('duplicate JSON member: ' + key)
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValidationError('nonstandard JSON constant: ' + value)


def parse_synthetic_claims(raw):
    """Parse a complete explicit synthetic envelope before any database writes."""
    if type(raw) is not bytes or not raw or len(raw) > MAX_BYTES:
        raise ValidationError('nonempty UTF-8 bytes required, at most 1 MiB')
    try:
        envelope = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_object,
            parse_constant=_invalid_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValidationError('invalid synthetic JSON envelope') from error
    if type(envelope) is not dict or set(envelope) != {'schema', 'claims'}:
        raise ValidationError('exact schema and claims envelope required')
    if envelope['schema'] != SCHEMA:
        raise ValidationError('explicit supported synthetic schema required')
    records = envelope['claims']
    if type(records) is not list or not records:
        raise ValidationError('nonempty explicit claim list required')
    sha = hashlib.sha256(raw).hexdigest()
    claims = []
    for index, record in enumerate(records):
        if type(record) is not dict or set(record) != CLAIM_KEYS:
            raise ValidationError('exact raw claim keys required; provenance is derived from bytes')
        claims.append(RawClaim(**record, source_sha256=sha,
            locator='/claims/' + str(index) + '/literal'))
    return tuple(claims)


def import_synthetic_claims(store, draft_id, *, expected_revision, operation_id, raw):
    """One atomic batch; an envelope cannot override development guards or context."""
    claims = parse_synthetic_claims(raw)
    return store.append(draft_id, expected_revision=expected_revision,
        operation_id=operation_id, claims=claims)
