"""Explicit synthetic source formats, preserving JSON backward compatibility."""
from .drafts import ValidationError
from .intake import MAX_BYTES, parse_synthetic_claims
from .sheets import parse_synthetic_sheet


def parse_source_claims(raw):
    if type(raw) is not bytes or not raw or len(raw) > MAX_BYTES:
        raise ValidationError('bounded nonempty synthetic source bytes required')
    # No dialect/header/locale guessing: each parser requires its own explicit schema.
    if raw.lstrip().startswith(b'{'):
        return parse_synthetic_claims(raw)
    return parse_synthetic_sheet(raw)


def import_synthetic_source(store, draft_id, *, expected_revision, operation_id, raw):
    claims = parse_source_claims(raw)
    return store.append(draft_id, expected_revision=expected_revision,
        operation_id=operation_id, claims=claims)
