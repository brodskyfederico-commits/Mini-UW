"""T04 explicit synthetic CSV sheet adapter; never executes spreadsheet content."""
import csv
import hashlib
import io

from .drafts import RawClaim, ValidationError
from .intake import MAX_BYTES

SCHEMA = 'miniuw.synthetic-sheet.v1'
COLUMNS = ('claim_id', 'slot_kind', 'slot_id', 'literal', 'unit_literal',
    'currency_literal', 'period_literal', 'definition_ref')
MAX_RECORDS = 10_000
MAX_FIELD_CHARS = 65_536


def _cell(value):
    if value == '\\N':
        return None
    if value.startswith('\\\\'):
        return value[1:]
    if value.startswith('\\'):
        raise ValidationError('CSV backslash must be doubled, except explicit null \\N')
    return value  # Preserve empty string, zero text, spaces and formula text.


def parse_synthetic_sheet(raw):
    if type(raw) is not bytes or not raw or len(raw) > MAX_BYTES:
        raise ValidationError('nonempty UTF-8 sheet bytes required, at most 1 MiB')
    try:
        text = raw.decode('utf-8')
        rows = csv.reader(io.StringIO(text, newline=''), delimiter=',', quotechar='"', strict=True)
        if next(rows, None) != [SCHEMA] or next(rows, None) != list(COLUMNS):
            raise ValidationError('exact synthetic marker and ordered CSV columns required')
        sha = hashlib.sha256(raw).hexdigest()
        claims = []
        for index, row in enumerate(rows, start=3):
            if len(claims) >= MAX_RECORDS or len(row) != len(COLUMNS):
                raise ValidationError('wrong CSV width or too many records; blank rows are not skipped')
            if any(len(cell) > MAX_FIELD_CHARS for cell in row):
                raise ValidationError('CSV field exceeds technical character bound')
            record = dict(zip(COLUMNS, (_cell(cell) for cell in row)))
            claims.append(RawClaim(**record, source_sha256=sha,
                locator='csv:record:' + str(index) + ':column:D'))
    except (UnicodeDecodeError, csv.Error) as error:
        raise ValidationError('invalid UTF-8 or malformed synthetic CSV') from error
    if not claims:
        raise ValidationError('at least one explicit synthetic claim row required')
    return tuple(claims)
