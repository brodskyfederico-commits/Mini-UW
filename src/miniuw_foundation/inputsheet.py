"""T06 exact original Inputs layout, accepted only as an explicitly synthetic copy."""
import json
import re
from pathlib import Path

from .drafts import RawClaim, ValidationError, canonical, template
from .workbooks import (MAIN, DOC_REL, WorkbookInspection, _parts, _xml,
    _relationships, _text, _read_cell, parse_synthetic_xlsx)
import hashlib

SCHEMA = 'miniuw.synthetic-inputs.v1'


def layout():
    data = json.loads((Path(__file__).parent/'data/input-sheet-layout-v1.json').read_bytes())
    draft, _ = template()
    expected = {f['field_id']:f['source_cell'].split('!')[1] for family in
        ('project_inputs','financing_inputs','requested_alternatives') for f in draft[family]}
    actual = {f['field_id']:f['value_cell'] for f in data['fields']}
    if actual != expected or len(data['fields']) != 55 or data['marker'] != SCHEMA:
        raise ValidationError('layout map disagrees with the unchanged input template')
    return data


def inspect_synthetic_input_sheet(raw):
    spec = layout()
    parts = _parts(raw)
    required = {'[Content_Types].xml','_rels/.rels','xl/workbook.xml','xl/_rels/workbook.xml.rels'}
    if not required <= parts.keys():
        raise ValidationError('missing input workbook metadata')
    types = _xml(parts['[Content_Types].xml'])
    if types.tag != '{http://schemas.openxmlformats.org/package/2006/content-types}Types' or any('macro' in e.get('ContentType','').lower() or 'vbaproject' in e.get('ContentType','').lower() for e in types):
        raise ValidationError('unsupported or macro-enabled content types')
    for name,value in parts.items():
        if name.endswith('.rels'):
            _relationships(value)
    roots = _relationships(parts['_rels/.rels'])
    if [target for kind,target in roots.values() if kind == DOC_REL+'/officeDocument'] != ['xl/workbook.xml']:
        raise ValidationError('explicit input workbook relationship required')
    book = _xml(parts['xl/workbook.xml'])
    sheets = book.findall('{'+MAIN+'}sheets/{'+MAIN+'}sheet')
    if book.tag != '{'+MAIN+'}workbook' or len(sheets) != 1 or sheets[0].get('name') != 'Inputs' or sheets[0].get('state','visible') != 'visible':
        raise ValidationError('one visible Inputs worksheet required')
    links = _relationships(parts['xl/_rels/workbook.xml.rels'])
    identity = sheets[0].get('{'+DOC_REL+'}id')
    if identity not in links or links[identity][0] != DOC_REL+'/worksheet':
        raise ValidationError('explicit Inputs worksheet relationship required')
    target = links[identity][1]
    part = target.lstrip('/') if target.startswith('/') else 'xl/'+target
    if part not in parts or not part.startswith('xl/worksheets/'):
        raise ValidationError('Inputs worksheet part unavailable')
    strings = []
    string_targets = [t for kind,t in links.values() if kind == DOC_REL+'/sharedStrings']
    if len(string_targets) > 1:
        raise ValidationError('ambiguous input shared strings')
    if string_targets:
        target = string_targets[0]
        path = target.lstrip('/') if target.startswith('/') else 'xl/'+target
        if path not in parts:
            raise ValidationError('input shared strings unavailable')
        table = _xml(parts[path])
        if table.tag != '{'+MAIN+'}sst':
            raise ValidationError('unsupported shared string table')
        strings = [_text(si) for si in table.findall('{'+MAIN+'}si')]
    sheet = _xml(parts[part])
    if sheet.tag != '{'+MAIN+'}worksheet' or len(sheet.findall('{'+MAIN+'}sheetData')) != 1:
        raise ValidationError('one explicit input data table required')
    if any(c.get('hidden') in ('1','true') for c in sheet.findall('{'+MAIN+'}cols/{'+MAIN+'}col')):
        raise ValidationError('hidden input columns unsupported')
    merges = [x.get('ref') for x in sheet.findall('{'+MAIN+'}mergeCells/{'+MAIN+'}mergeCell')]
    if sorted(merges) != spec['merged_ranges']:
        raise ValidationError('input merged regions differ from original documented layout')
    cells, rows = {}, set()
    for row in sheet.findall('{'+MAIN+'}sheetData/{'+MAIN+'}row'):
        number = row.get('r')
        if number not in spec['rows'] or number in rows or row.get('hidden') in ('1','true'):
            raise ValidationError('unknown, duplicate or hidden Inputs row')
        rows.add(number)
        for cell in row:
            ref = cell.get('r','')
            if cell.tag != '{'+MAIN+'}c' or not re.fullmatch('[A-G]'+number,ref) or ref not in spec['allowed_cells'] or ref in cells:
                raise ValidationError('unknown, moved or duplicate Inputs cell')
            cells[ref] = _read_cell(cell,strings,part)
    if rows != set(spec['rows']):
        raise ValidationError('documented input rows changed or omitted')
    for ref,expected in dict(spec['fixed_text'],G1=SCHEMA).items():
        value = cells.get(ref,{})
        if value.get('kind') != 'text' or value.get('literal') != expected:
            raise ValidationError('input label/unit/requirement/note/header or synthetic marker changed: '+ref)
    for field in spec['fields']:
        ref = field['value_cell']
        cells.setdefault(ref,{'kind':'missing','literal':None,'cell_type':None,
            'formula':None,'formula_attributes':None,'cached_value':None,
            'error_value':None,'style_id':None,'sheet_part':part})
        source = cells.get(field['source_text_cell'])
        if source and source['kind'] not in ('blank','text'):
            raise ValidationError('source-description column requires plain text or blank; never authenticated')
    for ref in ('B3','E3'):
        if ref in cells and cells[ref]['kind'] not in ('blank','text','numeric_lexeme'):
            raise ValidationError('deal/date metadata cannot use formulas or errors')
    return WorkbookInspection(hashlib.sha256(raw).hexdigest(),canonical(cells))


def parse_synthetic_input_sheet(raw):
    inspection = inspect_synthetic_input_sheet(raw)
    cells = inspection.cells
    return tuple(RawClaim(claim_id='native:'+inspection.source_sha256+':'+f['field_id'],
        slot_kind='input',slot_id=f['field_id'],
        literal=cells[f['value_cell']]['literal'],
        unit_literal=cells[f['unit_cell']]['literal'],
        currency_literal=None,period_literal=None,
        source_sha256=inspection.source_sha256,
        locator='xlsx:sheet:Inputs:cell:'+f['value_cell'],
        definition_ref='input-sheet-layout-v1') for f in layout()['fields'])


def parse_workbook_source(raw):
    parts = _parts(raw)
    if 'xl/workbook.xml' not in parts:
        raise ValidationError('workbook part missing')
    names = [s.get('name') for s in _xml(parts['xl/workbook.xml']).findall('{'+MAIN+'}sheets/{'+MAIN+'}sheet')]
    if names == ['Inputs']:
        return parse_synthetic_input_sheet(raw)
    return parse_synthetic_xlsx(raw)
