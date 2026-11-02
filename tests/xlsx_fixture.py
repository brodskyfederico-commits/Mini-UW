"""Minimal deterministic OOXML fixture writer for the documented synthetic profile."""
import io
import zipfile
import xml.etree.ElementTree as ET

M='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R='http://schemas.openxmlformats.org/package/2006/relationships'
D='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
C='http://schemas.openxmlformats.org/package/2006/content-types'
HEADER=('claim_id','slot_kind','slot_id','literal','unit_literal','currency_literal','period_literal','definition_ref')


def workbook(slot, *, literals=None, rows=None, shared=False, replacements=None, extras=None):
    records=rows or [['xlsx-claim','input',slot,'abc',chr(92)+'N',chr(92)+'N',chr(92)+'N','fixture-v1']]
    worksheet=ET.Element('{'+M+'}worksheet')
    data=ET.SubElement(worksheet,'{'+M+'}sheetData')
    strings=[]
    for number,values in enumerate([['miniuw.synthetic-xlsx.v1'],list(HEADER)]+records,start=1):
        row=ET.SubElement(data,'{'+M+'}row',r=str(number))
        for index,value in enumerate(values):
            ref=chr(65+index)+str(number)
            descriptor=(literals or {}).get(ref)
            if descriptor=='missing':continue
            if descriptor is not None:
                cell=ET.SubElement(row,'{'+M+'}c',r=ref,**descriptor.get('attributes',{}))
                if 'formula' in descriptor:
                    formula=ET.SubElement(cell,'{'+M+'}f',descriptor.get('formula_attributes',{}))
                    formula.text=descriptor['formula']
                if 'value' in descriptor:ET.SubElement(cell,'{'+M+'}v').text=descriptor['value']
            elif shared:
                cell=ET.SubElement(row,'{'+M+'}c',r=ref,t='s')
                strings.append(value)
                ET.SubElement(cell,'{'+M+'}v').text=str(len(strings)-1)
            else:
                cell=ET.SubElement(row,'{'+M+'}c',r=ref,t='inlineStr')
                inline=ET.SubElement(cell,'{'+M+'}is')
                ET.SubElement(inline,'{'+M+'}t').text=value
    book=ET.Element('{'+M+'}workbook')
    sheets=ET.SubElement(book,'{'+M+'}sheets')
    ET.SubElement(sheets,'{'+M+'}sheet',{'name':'Synthetic','sheetId':'1','{'+D+'}id':'rId1'})
    links=ET.Element('{'+R+'}Relationships')
    ET.SubElement(links,'{'+R+'}Relationship',Id='rId1',Type=D+'/worksheet',Target='worksheets/sheet1.xml')
    rootlinks=ET.Element('{'+R+'}Relationships')
    ET.SubElement(rootlinks,'{'+R+'}Relationship',Id='rId1',Type=D+'/officeDocument',Target='xl/workbook.xml')
    types=ET.Element('{'+C+'}Types')
    ET.SubElement(types,'{'+C+'}Default',Extension='rels',ContentType='application/vnd.openxmlformats-package.relationships+xml')
    ET.SubElement(types,'{'+C+'}Default',Extension='xml',ContentType='application/xml')
    ET.SubElement(types,'{'+C+'}Override',PartName='/xl/workbook.xml',ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml')
    ET.SubElement(types,'{'+C+'}Override',PartName='/xl/worksheets/sheet1.xml',ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml')
    parts={'[Content_Types].xml':ET.tostring(types),'_rels/.rels':ET.tostring(rootlinks),
        'xl/workbook.xml':ET.tostring(book),'xl/_rels/workbook.xml.rels':None,
        'xl/worksheets/sheet1.xml':ET.tostring(worksheet)}
    if shared:
        table=ET.Element('{'+M+'}sst',count=str(len(strings)),uniqueCount=str(len(strings)))
        for value in strings:
            item=ET.SubElement(table,'{'+M+'}si');ET.SubElement(item,'{'+M+'}t').text=value
        parts['xl/sharedStrings.xml']=ET.tostring(table)
        ET.SubElement(links,'{'+R+'}Relationship',Id='rId2',Type=D+'/sharedStrings',Target='sharedStrings.xml')
    parts['xl/_rels/workbook.xml.rels']=ET.tostring(links)
    parts.update(extras or {})
    for name,replace in (replacements or {}).items():
        if callable(replace):parts[name]=replace(parts[name])
        elif replace is None:parts.pop(name,None)
        else:parts[name]=replace
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,raw in sorted(parts.items()):
            entry=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(entry,raw)
    return output.getvalue()
