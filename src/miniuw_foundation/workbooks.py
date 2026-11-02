"""T05 bounded, nonexecuting reader for an explicit synthetic XLSX table profile."""
from dataclasses import dataclass
import hashlib
import io
import json
import re
from pathlib import PurePosixPath
import xml.etree.ElementTree as ET
import zipfile
import zlib

from .drafts import RawClaim, ValidationError, canonical
from .intake import MAX_BYTES
from .sheets import COLUMNS, MAX_FIELD_CHARS, MAX_RECORDS, _cell

SCHEMA = 'miniuw.synthetic-xlsx.v1'
SHEET = 'Synthetic'
MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
DOC_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
MAX_PART = 1_048_576
MAX_EXPANDED = 4_194_304


def _xml(raw):
    try:
        text = raw.decode('utf-8')
        if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
            raise ValidationError('XML DTD/entity declarations unsupported')
        return ET.fromstring(text)
    except (UnicodeError, ET.ParseError) as error:
        raise ValidationError('invalid UTF-8 XML workbook part') from error


def _parts(raw):
    if type(raw) is not bytes or not raw or len(raw) > MAX_BYTES:
        raise ValidationError('bounded nonempty synthetic XLSX bytes required')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            if not infos or len(infos) > 64 or len({i.filename for i in infos}) != len(infos):
                raise ValidationError('duplicate entries or too many XLSX parts')
            if sum(i.file_size for i in infos) > MAX_EXPANDED:
                raise ValidationError('expanded workbook exceeds technical bound')
            parts = {}
            for info in infos:
                path = PurePosixPath(info.filename)
                if (path.is_absolute() or '..' in path.parts or '\\' in info.filename
                    or info.is_dir() or (info.external_attr >> 16) & 0o170000 == 0o120000
                    or info.flag_bits & 1 or info.compress_type not in (0,8)
                    or info.file_size > MAX_PART):
                    raise ValidationError('unsupported or unsafe XLSX entry')
                lowered = info.filename.lower()
                if any(x in lowered for x in ('vbaproject','externallinks/','embeddings/')):
                    raise ValidationError('macros, external links and embedded payloads unsupported')
                with archive.open(info) as stream:
                    value = stream.read(MAX_PART + 1)
                if len(value) > MAX_PART:
                    raise ValidationError('workbook part exceeds technical bound')
                parts[info.filename] = value
            if sum(map(len,parts.values())) > MAX_EXPANDED:
                raise ValidationError('actual expanded workbook exceeds technical bound')
            return parts
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, zlib.error) as error:
        raise ValidationError('invalid or unsupported XLSX ZIP') from error


def _relationships(raw):
    root = _xml(raw)
    if root.tag != '{'+REL+'}Relationships':
        raise ValidationError('unsupported relationships namespace')
    result = {}
    for element in root:
        if element.tag != '{'+REL+'}Relationship':
            raise ValidationError('unsupported relationship')
        identity, target = element.get('Id'), element.get('Target')
        if not identity or identity in result or not target or element.get('TargetMode','Internal') != 'Internal':
            raise ValidationError('ambiguous or external workbook relationship')
        if '..' in PurePosixPath(target).parts or '\\' in target or ':' in target:
            raise ValidationError('unsupported relationship target')
        result[identity] = (element.get('Type'), target)
    return result


def _text(element):
    if any(child.tag not in ('{'+MAIN+'}t','{'+MAIN+'}r') for child in element):
        raise ValidationError('unsupported rich text structure')
    return ''.join(t.text or '' for t in element.iter('{'+MAIN+'}t'))


@dataclass(frozen=True)
class WorkbookInspection:
    source_sha256: str
    cells_json: str

    @property
    def cells(self):
        return json.loads(self.cells_json)


def inspect_synthetic_xlsx(raw):
    parts = _parts(raw)
    required = {'[Content_Types].xml','_rels/.rels','xl/workbook.xml','xl/_rels/workbook.xml.rels'}
    if not required <= parts.keys():
        raise ValidationError('missing workbook package metadata')
    content_types = _xml(parts['[Content_Types].xml'])
    if content_types.tag != '{http://schemas.openxmlformats.org/package/2006/content-types}Types':
        raise ValidationError('unsupported content types namespace')
    if any('macroenabled' in (e.get('ContentType','').lower()) or 'vbaproject' in e.get('ContentType','').lower() for e in content_types):
        raise ValidationError('macro-enabled content unsupported')
    for name, value in parts.items():
        if name.endswith('.rels'):
            _relationships(value)  # Never follow external links, including unrelated parts.
    root_links = _relationships(parts['_rels/.rels'])
    offices = [target for kind,target in root_links.values() if kind == DOC_REL+'/officeDocument']
    if offices != ['xl/workbook.xml']:
        raise ValidationError('explicit workbook relationship required')
    workbook = _xml(parts['xl/workbook.xml'])
    if workbook.tag != '{'+MAIN+'}workbook':
        raise ValidationError('unsupported workbook namespace')
    sheets = workbook.findall('{'+MAIN+'}sheets/{'+MAIN+'}sheet')
    if len(sheets) != 1 or sheets[0].get('name') != SHEET or sheets[0].get('state','visible') != 'visible':
        raise ValidationError('one visible Synthetic worksheet required')
    links = _relationships(parts['xl/_rels/workbook.xml.rels'])
    identity = sheets[0].get('{'+DOC_REL+'}id')
    if identity not in links or links[identity][0] != DOC_REL+'/worksheet':
        raise ValidationError('explicit worksheet relationship required')
    target = links[identity][1]
    sheet_part = target.lstrip('/') if target.startswith('/') else 'xl/'+target
    if sheet_part not in parts or not sheet_part.startswith('xl/worksheets/'):
        raise ValidationError('worksheet part unavailable')
    strings = []
    string_links = [target for kind,target in links.values() if kind == DOC_REL+'/sharedStrings']
    if len(string_links) > 1:
        raise ValidationError('ambiguous shared string tables')
    if string_links:
        target = string_links[0]
        path = target.lstrip('/') if target.startswith('/') else 'xl/'+target
        if path not in parts:
            raise ValidationError('shared strings part unavailable')
        table = _xml(parts[path])
        if table.tag != '{'+MAIN+'}sst':
            raise ValidationError('unsupported shared string table')
        strings = [_text(si) for si in table.findall('{'+MAIN+'}si')]
    worksheet = _xml(parts[sheet_part])
    if worksheet.tag != '{'+MAIN+'}worksheet' or worksheet.find('{'+MAIN+'}mergeCells') is not None:
        raise ValidationError('unsupported worksheet namespace or merged cells')
    if any(col.get('hidden') in ('1','true') for col in worksheet.findall('{'+MAIN+'}cols/{'+MAIN+'}col')):
        raise ValidationError('hidden columns unsupported')
    if len(worksheet.findall('{'+MAIN+'}sheetData')) != 1:
        raise ValidationError('one explicit worksheet data table required')
    cells, rows = {}, set()
    for row in worksheet.findall('{'+MAIN+'}sheetData/{'+MAIN+'}row'):
        number = row.get('r','')
        if len(number) > 5 or not re.fullmatch('[1-9][0-9]*',number) or int(number) > MAX_RECORDS+2 or number in rows or row.get('hidden') in ('1','true'):
            raise ValidationError('invalid, duplicate or hidden worksheet row')
        rows.add(number)
        for cell in row:
            reference = cell.get('r','')
            match = re.fullmatch('([A-H])([1-9][0-9]*)',reference)
            if cell.tag != '{'+MAIN+'}c' or not match or match[2] != number or reference in cells:
                raise ValidationError('invalid, out-of-profile or duplicate cell coordinate')
            formulas = cell.findall('{'+MAIN+'}f')
            values = cell.findall('{'+MAIN+'}v')
            inlines = cell.findall('{'+MAIN+'}is')
            if len(inlines) > 1 or (inlines and (formulas or values or cell.get('t') != 'inlineStr')):
                raise ValidationError('ambiguous inline/formula/value cell')
            if any(child.tag not in ('{'+MAIN+'}f','{'+MAIN+'}v','{'+MAIN+'}is') for child in cell):
                raise ValidationError('unsupported cell element')
            if len(formulas) > 1 or len(values) > 1:
                raise ValidationError('ambiguous cell formula/value')
            value = values[0].text if values else None
            kind, literal = 'blank', None
            cell_type = cell.get('t','n')
            if formulas:
                kind = 'formula'
            elif cell_type == 'inlineStr':
                inline = cell.find('{'+MAIN+'}is')
                if inline is None or values:
                    raise ValidationError('invalid inline string cell')
                kind, literal = 'text', _text(inline)
            elif cell_type == 's':
                if value is None or len(value) > 7 or not value.isascii() or not value.isdigit() or int(value) >= len(strings):
                    raise ValidationError('invalid shared string index')
                kind, literal = 'text', strings[int(value)]
            elif cell_type == 'n' and value is not None:
                if not re.fullmatch(r'[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?',value):
                    raise ValidationError('invalid numeric lexeme')
                kind, literal = 'numeric_lexeme', value
            elif cell_type == 'e':
                kind = 'excel_error'
            elif cell_type != 'n':
                raise ValidationError('unsupported XLSX cell type; no coercion')
            if any(len(x or '') > MAX_FIELD_CHARS for x in (literal,value,formulas[0].text if formulas else None)):
                raise ValidationError('cell exceeds technical text bound')
            cells[reference] = {'kind':kind,'literal':literal,'cell_type':cell_type,
                'formula':formulas[0].text if formulas else None,
                'formula_attributes':dict(formulas[0].attrib) if formulas else None,
                'cached_value':value if formulas else None,
                'error_value':value if kind == 'excel_error' else None,
                'style_id':cell.get('s'), 'sheet_part':sheet_part}
    def text_at(reference):
        record = cells.get(reference,{})
        if record.get('kind') != 'text':
            raise ValidationError('explicit text marker/header required')
        return record['literal']
    if text_at('A1') != SCHEMA or any(ref != 'A1' and ref.endswith('1') and re.fullmatch('[A-H]1',ref) for ref in cells):
        raise ValidationError('exact synthetic XLSX marker required')
    if [text_at(chr(65+i)+'2') for i in range(8)] != list(COLUMNS):
        raise ValidationError('exact ordered sheet headers required')
    row_numbers = sorted(int(r) for r in rows)
    if row_numbers != list(range(1,max(row_numbers,default=0)+1)) or len(rows) < 3:
        raise ValidationError('explicit contiguous table rows required')
    for number in row_numbers[2:]:
        for column in 'ABCEFGH':
            if cells.get(column+str(number),{}).get('kind') != 'text':
                raise ValidationError('metadata cells must be explicit text; no formula/cache identity')
        cells.setdefault('D'+str(number),{'kind':'missing','literal':None,
            'cell_type':None,'formula':None,'formula_attributes':None,'cached_value':None,
            'error_value':None,'style_id':None,'sheet_part':sheet_part})
    return WorkbookInspection(hashlib.sha256(raw).hexdigest(),canonical(cells))


def parse_synthetic_xlsx(raw):
    inspection = inspect_synthetic_xlsx(raw)
    cells, claims = inspection.cells, []
    rows = sorted(int(ref[1:]) for ref in cells if ref.startswith('A') and int(ref[1:]) >= 3)
    for number in rows:
        record = {name:_cell(cells[chr(65+i)+str(number)]['literal'])
            for i,name in enumerate(COLUMNS) if i != 3}
        source = cells['D'+str(number)]
        record['literal'] = (_cell(source['literal']) if source['kind'] == 'text'
            else source['literal'] if source['kind'] == 'numeric_lexeme' else None)
        claims.append(RawClaim(**record,source_sha256=inspection.source_sha256,
            locator='xlsx:sheet:Synthetic:cell:D'+str(number)))
    return tuple(claims)
