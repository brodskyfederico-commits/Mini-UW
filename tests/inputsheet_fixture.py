"""Generate synthetic copies of the supplied blank layout, without changing its bytes."""
from pathlib import Path
import io
import zipfile
import xml.etree.ElementTree as ET

M='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
ORIGINAL=Path(__file__).resolve().parents[1]/'sources/originals/b433468ec6cb__Input_Sheet_vigente_original.xlsx'


def native_workbook(values=None, *, marker=True, edit=None):
    with zipfile.ZipFile(io.BytesIO(ORIGINAL.read_bytes())) as archive:
        parts={name:archive.read(name) for name in archive.namelist()}
    root=ET.fromstring(parts['xl/worksheets/sheet1.xml'])
    data=root.find('{'+M+'}sheetData')
    if marker:
        values=dict(values or {},G1={'text':'miniuw.synthetic-inputs.v1'})
    for ref,descriptor in (values or {}).items():
        number=''.join(c for c in ref if c.isdigit())
        row=next((r for r in data if r.get('r')==number),None)
        if row is None:row=ET.SubElement(data,'{'+M+'}row',r=number)
        previous=next((c for c in row if c.get('r')==ref),None)
        if previous is not None:row.remove(previous)
        if descriptor=='missing':continue
        cell=ET.SubElement(row,'{'+M+'}c',r=ref)
        if 'text' in descriptor:
            cell.set('t','inlineStr');inline=ET.SubElement(cell,'{'+M+'}is')
            ET.SubElement(inline,'{'+M+'}t').text=descriptor['text']
        else:
            cell.set('t',descriptor.get('type','n'))
            if 'formula' in descriptor:ET.SubElement(cell,'{'+M+'}f').text=descriptor['formula']
            if 'value' in descriptor:ET.SubElement(cell,'{'+M+'}v').text=descriptor['value']
    for row in data:
        row[:]=sorted(row,key=lambda c:c.get('r','').rstrip('0123456789'))
    dimension=root.find('{'+M+'}dimension')
    if marker and dimension is not None:dimension.set('ref','A1:G82')
    if edit:edit(root)
    parts['xl/worksheets/sheet1.xml']=ET.tostring(root)
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,value in sorted(parts.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,value)
    return output.getvalue()
