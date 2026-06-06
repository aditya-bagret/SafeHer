#!/usr/bin/env python3
"""Generate SafeHer project report document.xml based on template structure."""

import xml.sax.saxutils as saxutils

def esc(text):
    """Escape XML special characters."""
    return saxutils.escape(str(text))

def t(text):
    """Create a w:t element with proper space preservation."""
    return f'<w:t xml:space="preserve">{esc(text)}</w:t>'

def run(text, bold=False, italic=False, sz=None, spacing=None, color=None):
    """Create a w:r element."""
    rpr = ''
    props = []
    if bold:
        props.append('<w:b/><w:bCs/>')
    if italic:
        props.append('<w:i/><w:iCs/>')
    if sz:
        props.append(f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>')
    if color:
        props.append(f'<w:color w:val="{color}"/>')
    if props:
        rpr = f'<w:rPr>{"".join(props)}</w:rPr>'
    return f'<w:r>{rpr}{t(text)}</w:r>'

def para(runs_or_text, style='BodyText', bold=False, italic=False, sz=None,
         align=None, space_before=None, space_after=None, line=None,
         indent_left=None, indent_right=None, indent_hanging=None,
         page_break_before=False, keep_with_next=False):
    """Create a w:p paragraph element."""
    ppr_parts = [f'<w:pStyle w:val="{style}"/>']
    if page_break_before:
        ppr_parts.append('<w:pageBreakBefore/>')
    if keep_with_next:
        ppr_parts.append('<w:keepNext/>')
    
    spacing_parts = []
    if space_before is not None:
        spacing_parts.append(f'w:before="{space_before}"')
    if space_after is not None:
        spacing_parts.append(f'w:after="{space_after}"')
    if line is not None:
        spacing_parts.append(f'w:line="{line}" w:lineRule="auto"')
    if spacing_parts:
        ppr_parts.append(f'<w:spacing {" ".join(spacing_parts)}/>')

    ind_parts = []
    if indent_left is not None:
        ind_parts.append(f'w:left="{indent_left}"')
    if indent_right is not None:
        ind_parts.append(f'w:right="{indent_right}"')
    if indent_hanging is not None:
        ind_parts.append(f'w:hanging="{indent_hanging}"')
    if ind_parts:
        ppr_parts.append(f'<w:ind {" ".join(ind_parts)}/>')

    if align:
        ppr_parts.append(f'<w:jc w:val="{align}"/>')

    ppr = f'<w:pPr>{"".join(ppr_parts)}</w:pPr>'

    if isinstance(runs_or_text, str):
        content = run(runs_or_text, bold=bold, italic=italic, sz=sz)
    elif isinstance(runs_or_text, list):
        content = ''.join(runs_or_text)
    else:
        content = runs_or_text

    return f'<w:p>{ppr}{content}</w:p>'

def empty_para(style='BodyText'):
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr></w:p>'

def page_break():
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'

def heading1(text):
    return para(run(text, bold=True, sz=28), style='Heading1', align='center', space_before='120', space_after='120')

def heading2(text):
    return para(run(text, bold=True, sz=24), style='Heading2', space_before='120', space_after='60')

def heading3(text):
    return para(run(text, bold=True, sz=24), style='Heading3', space_before='100', space_after='60')

def bold_center(text, sz=28):
    return para(run(text, bold=True, sz=sz), style='BodyText', align='center')

def center(text, sz=None):
    return para(run(text, sz=sz), style='BodyText', align='center')

def body(text, bold=False, italic=False):
    return para(run(text, bold=bold, italic=italic), style='BodyText', space_before='60', space_after='60', line='360')

def bullet(text, level=0):
    indent = 720 + level * 360
    r = run(text)
    return f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="{indent}" w:hanging="360"/></w:pPr><w:r><w:t xml:space="preserve">&#x2022;  {esc(text)}</w:t></w:r></w:p>'

def numbered(num, text):
    return f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720" w:hanging="360"/></w:pPr><w:r><w:t xml:space="preserve">[{num}] {esc(text)}</w:t></w:r></w:p>'

def section_break(footer_rid, top, right, bottom, left, w="11910", h="16840", header="0", footer_val="0"):
    """Create a paragraph with section break."""
    sect = f'''<w:sectPr w:rsidR="00BA6F7E">
          <w:footerReference w:type="default" r:id="{footer_rid}"/>
          <w:pgSz w:w="{w}" w:h="{h}"/>
          <w:pgMar w:top="{top}" w:right="{right}" w:bottom="{bottom}" w:left="{left}" w:header="{header}" w:footer="{footer_val}" w:gutter="0"/>
          <w:cols w:space="720"/>
        </w:sectPr>'''
    return f'<w:p><w:pPr>{sect}</w:pPr></w:p>'

def final_section(top="1040", right="560", bottom="280", left="540"):
    return f'''<w:sectPr w:rsidR="00BA6F7E">
      <w:pgSz w:w="11900" w:h="16850"/>
      <w:pgMar w:top="{top}" w:right="{right}" w:bottom="{bottom}" w:left="{left}" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>'''

def make_table(headers, rows, col_widths, header_sz=24, cell_sz=24):
    """Create a table with headers and rows."""
    total_w = sum(col_widths)
    col_widths_str = ''.join(f'<w:gridCol w:w="{w}"/>' for w in col_widths)
    
    def cell(text, width, bold=False, sz=24):
        b = '<w:b/><w:bCs/>' if bold else ''
        return f'''<w:tc>
            <w:tcPr>
              <w:tcW w:w="{width}" w:type="dxa"/>
              <w:tcBorders>
                <w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>
                <w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/>
                <w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>
                <w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/>
              </w:tcBorders>
              <w:shd w:val="clear" w:color="auto" w:fill="auto"/>
              <w:tcMar><w:top w:w="60" w:type="dxa"/><w:left w:w="108" w:type="dxa"/><w:bottom w:w="60" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tcMar>
            </w:tcPr>
            <w:p><w:pPr><w:pStyle w:val="TableParagraph"/></w:pPr><w:r><w:rPr>{b}<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/></w:rPr>{t(text)}</w:r></w:p>
          </w:tc>'''
    
    header_row = '<w:tr>' + ''.join(cell(h, w, bold=True, sz=header_sz) for h, w in zip(headers, col_widths)) + '</w:tr>'
    
    data_rows = ''
    for row in rows:
        cells_xml = ''.join(cell(c, w, sz=cell_sz) for c, w in zip(row, col_widths))
        data_rows += f'<w:tr>{cells_xml}</w:tr>'
    
    return f'''<w:tbl>
        <w:tblPr>
          <w:tblW w:w="{total_w}" w:type="dxa"/>
          <w:tblBorders>
            <w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>
            <w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/>
            <w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>
            <w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/>
            <w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/>
            <w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/>
          </w:tblBorders>
          <w:tblCellMar>
            <w:top w:w="60" w:type="dxa"/>
            <w:left w:w="108" w:type="dxa"/>
            <w:bottom w:w="60" w:type="dxa"/>
            <w:right w:w="108" w:type="dxa"/>
          </w:tblCellMar>
        </w:tblPr>
        <w:tblGrid>{col_widths_str}</w:tblGrid>
        {header_row}
        {data_rows}
      </w:tbl>'''

def image_drawing(rid, pic_id, name, cx, cy, pos_h, pos_v, wrap="wrapTopAndBottom"):
    """Create an anchored image drawing."""
    wrap_xml = f'<wp:{wrap}/>'
    return f'''<w:drawing>
          <wp:anchor distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="251655680" behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1" wp14:anchorId="{pic_id}" wp14:editId="00000001">
            <wp:simplePos x="0" y="0"/>
            <wp:positionH relativeFrom="page">
              <wp:posOffset>{pos_h}</wp:posOffset>
            </wp:positionH>
            <wp:positionV relativeFrom="paragraph">
              <wp:posOffset>{pos_v}</wp:posOffset>
            </wp:positionV>
            <wp:extent cx="{cx}" cy="{cy}"/>
            <wp:effectExtent l="0" t="0" r="0" b="9525"/>
            {wrap_xml}
            <wp:docPr id="{pic_id[4:]}" name="{name}"/>
            <wp:cNvGraphicFramePr>
              <a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/>
            </wp:cNvGraphicFramePr>
            <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
              <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
                <pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
                  <pic:nvPicPr>
                    <pic:cNvPr id="{pic_id[4:]}" name="{name}"/>
                    <pic:cNvPicPr><a:picLocks noChangeAspect="1"/></pic:cNvPicPr>
                  </pic:nvPicPr>
                  <pic:blipFill>
                    <a:blip r:embed="{rid}" cstate="print"/>
                    <a:stretch><a:fillRect/></a:stretch>
                  </pic:blipFill>
                  <pic:spPr>
                    <a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
                    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
                  </pic:spPr>
                </pic:pic>
              </a:graphicData>
            </a:graphic>
          </wp:anchor>
        </w:drawing>'''

# ============================================================
# BUILD THE DOCUMENT
# ============================================================

DOC_OPEN = '''<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" xmlns:cx="http://schemas.microsoft.com/office/drawing/2014/chartex" xmlns:cx1="http://schemas.microsoft.com/office/drawing/2015/9/8/chartex" xmlns:cx2="http://schemas.microsoft.com/office/drawing/2015/10/21/chartex" xmlns:cx3="http://schemas.microsoft.com/office/drawing/2016/5/9/chartex" xmlns:cx4="http://schemas.microsoft.com/office/drawing/2016/5/10/chartex" xmlns:cx5="http://schemas.microsoft.com/office/drawing/2016/5/11/chartex" xmlns:cx6="http://schemas.microsoft.com/office/drawing/2016/5/12/chartex" xmlns:cx7="http://schemas.microsoft.com/office/drawing/2016/5/13/chartex" xmlns:cx8="http://schemas.microsoft.com/office/drawing/2016/5/14/chartex" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:aink="http://schemas.microsoft.com/office/drawing/2016/ink" xmlns:am3d="http://schemas.microsoft.com/office/drawing/2017/model3d" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:oel="http://schemas.microsoft.com/office/2019/extlst" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:w10="urn:schemas-microsoft-com:office:word" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml" xmlns:w16cex="http://schemas.microsoft.com/office/word/2018/wordml/cex" xmlns:w16cid="http://schemas.microsoft.com/office/word/2016/wordml/cid" xmlns:w16="http://schemas.microsoft.com/office/word/2018/wordml" xmlns:w16du="http://schemas.microsoft.com/office/word/2023/wordml/word16du" xmlns:w16sdtdh="http://schemas.microsoft.com/office/word/2020/wordml/sdtdatahash" xmlns:w16sdtfl="http://schemas.microsoft.com/office/word/2024/wordml/sdtformatlock" xmlns:w16se="http://schemas.microsoft.com/office/word/2015/wordml/symex" xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" mc:Ignorable="w14 w15 w16se w16cid w16 w16cex w16sdtdh w16sdtfl w16du wp14">
  <w:body>'''

parts = []

# ============================================================
# COVER PAGE (Section 1 - footer rId9)
# ============================================================
parts.append(empty_para())
parts.append(empty_para())
parts.append(bold_center('SRM INSTITUTE OF SCIENCE AND TECHNOLOGY', sz=28))
parts.append(bold_center('DEPARTMENT OF COMPUTATIONAL INTELLIGENCE', sz=26))
parts.append(bold_center('COLLEGE OF ENGINEERING AND TECHNOLOGY', sz=26))
parts.append(center('KATTANKULATHUR &#x2013; 603 203', sz=24))
parts.append(empty_para())
# SRM Logo (rId8)
logo_drawing = image_drawing('rId8', 'AAAA0001', 'SRM_Logo.jpeg', '2251710', '828675', '2714625', '250190')
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:jc w:val="center"/></w:pPr><w:r>{logo_drawing}</w:r></w:p>')
parts.append(empty_para())
parts.append(bold_center('21CSP302L &#x2013; MINOR RESEARCH PROJECT', sz=28))
parts.append(empty_para())
parts.append(bold_center('SafeHer: AI-Powered Women Safety and Emergency Response System', sz=28))
parts.append(empty_para())
parts.append(para(run('in partial fulfillment of the requirements for the degree of', italic=True, sz=24), style='BodyText', align='center'))
parts.append(empty_para())
parts.append(bold_center('BACHELOR OF TECHNOLOGY', sz=28))
parts.append(bold_center('in', sz=28))
parts.append(bold_center('COMPUTER SCIENCE AND ENGINEERING', sz=28))
parts.append(center('with specialization in Data Science and Business Systems', sz=24))
parts.append(empty_para())
parts.append(bold_center('Submitted by', sz=26))
parts.append(empty_para())
parts.append(bold_center('ADITYA SHARMA [RA2111003010042]', sz=26))
parts.append(bold_center('PARI GUPTA [RA2111003010047]', sz=26))
parts.append(empty_para())
parts.append(para(run('Under the Guidance of', italic=True, sz=24), style='BodyText', align='center'))
parts.append(empty_para())
parts.append(bold_center('Dr. P. RAJASEKAR', sz=26))
parts.append(center('Associate Professor, Department of Data Science and Business Systems', sz=24))
parts.append(empty_para())
parts.append(empty_para())
parts.append(bold_center('DEPARTMENT OF COMPUTATIONAL INTELLIGENCE', sz=26))
parts.append(bold_center('COLLEGE OF ENGINEERING AND TECHNOLOGY', sz=26))
parts.append(bold_center('SRM INSTITUTE OF SCIENCE AND TECHNOLOGY', sz=26))
parts.append(bold_center('KATTANKULATHUR &#x2013; 603 203', sz=26))
parts.append(empty_para())
parts.append(bold_center('MAY 2026', sz=26))

# Section 1 break (cover page - footer rId9)
parts.append(section_break('rId9', top='1200', right='560', bottom='280', left='540', w='11900', h='16850', header='720', footer_val='720'))

# ============================================================
# OWN WORK DECLARATION PAGE (Section 2 - footer rId12)
# ============================================================
parts.append(empty_para())
# SRM logos for declaration page (rId10 and rId11)
logo2_drawing = image_drawing('rId10', 'BBBB0001', 'SRM_Logo2.jpeg', '1263650', '539750', '914400', '108585', wrap='wrapNone')
logo3_drawing = image_drawing('rId11', 'BBBB0002', 'SRM_Logo3.jpeg', '5412105', '1851660', '1059180', '166370')
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/></w:pPr><w:r>{logo2_drawing}</w:r></w:p>')
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:jc w:val="center"/></w:pPr><w:r>{logo3_drawing}</w:r></w:p>')
parts.append(empty_para())
parts.append(bold_center('SRM INSTITUTE OF SCIENCE AND TECHNOLOGY', sz=28))
parts.append(bold_center('KATTANKULATHUR &#x2013; 603 203', sz=26))
parts.append(empty_para())
parts.append(bold_center('OWN WORK DECLARATION FORM', sz=26))
parts.append(empty_para())
parts.append(body('This sheet must be filled in and signed, confirming that all conditions listed below have been met. It must be included with the submitted project report. Work will not be evaluated unless this form is properly completed.'))
parts.append(empty_para())

decl_table = make_table(
    ['Field', 'Details'],
    [
        ['Degree / Course', 'Bachelor of Technology in Computer Science and Engineering (Data Science and Business Systems)'],
        ['Student Names', 'Aditya Sharma [RA2111003010042], Pari Gupta [RA2111003010047]'],
        ['Registration Numbers', 'RA2111003010042, RA2111003010047'],
        ['Title of Work', 'SafeHer: AI-Powered Women Safety and Emergency Response System'],
    ],
    [3000, 6500]
)
parts.append(decl_table)
parts.append(empty_para())
parts.append(body('We hereby certify that this project report complies with the University\'s Rules and Regulations relating to academic misconduct and plagiarism. We confirm that:'))
parts.append(bullet('All sources have been clearly referenced and listed as appropriate.'))
parts.append(bullet('All quoted text has been placed in inverted commas with sources cited.'))
parts.append(bullet('Sources of all pictures, data, and figures not our own have been provided.'))
parts.append(bullet('We have not made use of reports or essays of any other student, past or present.'))
parts.append(bullet('Any help received from others (peers, technicians, external sources) has been duly acknowledged.'))
parts.append(bullet('We have complied with all plagiarism criteria specified in the course handbook.'))
parts.append(empty_para())
parts.append(body('We understand that any false claim in this work will be penalized in accordance with University policies and regulations.'))
parts.append(empty_para())

decl_sign_table = make_table(
    ['DECLARATION'],
    [['I am aware of the University\'s policy on Academic Misconduct and Plagiarism and certify that this assessment is our own work, except where indicated.\n\nAditya Sharma \u00a0\u00a0 <<Signature>> \u00a0\u00a0 Date: _____________\n\nPari Gupta \u00a0\u00a0 <<Signature>> \u00a0\u00a0 Date: _____________']],
    [9500]
)
parts.append(decl_sign_table)

# BONAFIDE CERTIFICATE
parts.append(page_break())
parts.append(empty_para())
parts.append(empty_para())
parts.append(bold_center('SRM INSTITUTE OF SCIENCE AND TECHNOLOGY', sz=28))
parts.append(bold_center('KATTANKULATHUR &#x2013; 603 203', sz=26))
parts.append(empty_para())
parts.append(bold_center('BONAFIDE CERTIFICATE', sz=28))
parts.append(empty_para())
parts.append(body([
    run('Certified that '),
    run('21CSP302L &#x2013; Minor Research Project', bold=True),
    run(' titled '),
    run('"SafeHer: AI-Powered Women Safety and Emergency Response System"', bold=True),
    run(' is the bonafide work of '),
    run('"Aditya Sharma [RA2111003010042] and Pari Gupta [RA2111003010047]"', bold=True),
    run(', who carried out the project work under my supervision. Certified further that, to the best of my knowledge, the work reported herein does not form part of any other project report or dissertation on the basis of which a degree or award was conferred on an earlier occasion on this or any other candidate.'),
]))
parts.append(empty_para())
parts.append(empty_para())

cert_table = make_table(
    ['SUPERVISOR', 'HEAD OF DEPARTMENT'],
    [
        ['<<Signature>>\nDr. P. RAJASEKAR\nAssociate Professor\nDepartment of Data Science and Business Systems\nSRM Institute of Science and Technology',
         '<<Signature>>\nDR. R. ANNIE UTHRA\nProfessor & Head\nDepartment of Computational Intelligence\nSRM Institute of Science and Technology']
    ],
    [4750, 4750]
)
parts.append(cert_table)
parts.append(empty_para())
parts.append(empty_para())
parts.append(body([run('EXAMINER 1: Name & Signature ________________________', bold=True), run('          '), run('EXAMINER 2: Name & Signature ________________________', bold=True)]))

# Section 2 break (Declaration + Certificate)
parts.append(section_break('rId12', top='567', right='570', bottom='280', left='426', w='11910', h='16840'))

# ============================================================
# ACKNOWLEDGEMENTS (Section 3 - footer rId14)
# ============================================================
parts.append(empty_para())
parts.append(bold_center('ACKNOWLEDGEMENTS', sz=28))
parts.append(empty_para())
parts.append(body('We express our humble gratitude to Dr. C. Muthamizhchelvan, Vice-Chancellor, SRM Institute of Science and Technology, for the facilities extended for the project work and his continued encouragement and support throughout our academic journey.'))
parts.append(body('We extend our sincere thanks to the Dean, College of Engineering and Technology, SRM Institute of Science and Technology, for his invaluable support and for fostering a culture of innovation and research within the institution.'))
parts.append(body('We wish to thank Dr. Revathi Venkataraman, Professor and Chairperson, School of Computing, SRM Institute of Science and Technology, for her continued support throughout the project work and for inspiring us to pursue meaningful research.'))
parts.append(body('We are incredibly grateful to the Head of the Department, Department of Data Science and Business Systems, SRM Institute of Science and Technology, for her suggestions and encouragement at all stages of our project work and for providing us with the resources needed to complete this research.'))
parts.append(body('We convey our sincere thanks to our Project Coordinators, Panel Head, and Panel Members, Department of Data Science and Business Systems, SRM Institute of Science and Technology, for their constructive inputs during the project reviews and for their guidance throughout the development process.'))
parts.append(body('We register our immeasurable thanks to our Faculty Advisor, Department of Data Science and Business Systems, SRM Institute of Science and Technology, for leading and helping us to complete our course and for continuously motivating us to achieve excellence.'))
parts.append(body([
    run('Our deepest respect and gratitude go to our guide, '),
    run('Dr. P. Rajasekar', bold=True),
    run(', Associate Professor, Department of Data Science and Business Systems, SRM Institute of Science and Technology, for providing us with the opportunity to pursue this project under his expert mentorship. His passion for solving real-world problems using artificial intelligence, his clarity of thought, and his commitment to research have been a constant source of inspiration. His guidance, freedom to explore, and timely support were invaluable in shaping this work.'),
]))
parts.append(body('We sincerely thank all the staff members of the Department of Data Science and Business Systems, School of Computing, SRM Institute of Science and Technology, for their assistance during our project. Finally, we would like to thank our parents, family members, and friends for their unconditional love, constant support, and unwavering encouragement throughout this journey.'))
parts.append(empty_para())
parts.append(para(run('Authors', bold=True), style='BodyText', align='right'))
parts.append(para(run('Aditya Sharma & Pari Gupta', bold=True), style='BodyText', align='right'))

# Section 3 break
parts.append(section_break('rId14', top='1260', right='930', bottom='280', left='1530', w='11910', h='16840'))

# ============================================================
# ABSTRACT (Section 4 - footer rId16)
# ============================================================
parts.append(empty_para())
parts.append(bold_center('ABSTRACT', sz=28))
parts.append(empty_para())
parts.append(body("Women's personal safety in urban environments remains one of the most pressing societal challenges of the twenty-first century. Existing navigation platforms such as Google Maps and Apple Maps optimise routes exclusively for time and distance, offering no mechanism for crime-risk-aware routing or real-time emergency response. SafeHer is a comprehensive AI-powered women safety and emergency response system that addresses this gap through an integrated multi-modal framework combining real-time crime risk prediction, GPS-based location tracking, instant SOS alert dispatch, and intelligent safe-route recommendation."))
parts.append(body('The system employs a two-component machine learning architecture trained on 8.4 million crime incidents from the City of Chicago Crimes Dataset (2001&#x2013;2025). A LightGBM regressor predicts spatial danger scores per 200-metre grid cell using a Crime Danger Index (CDI) percentile target&#x2014;achieving R&#xB2; = 0.9997 and High-Risk Precision of 99.2%&#x2014;while a 168-slot empirical temporal multiplier (violent crime rate by hour x day-of-week) modulates risk dynamically. Together, these components regenerate a full-city risk heatmap in under one second, over 100 times faster than CNN-LSTM baselines.'))
parts.append(body('The React.js frontend integrates with the Google Maps JavaScript API to render a live, colour-coded heatmap that visually changes as users drag an hour slider, and recommends up to three alternative driving routes ranked by safety. The Flask-based REST API ensures that heatmap colours and route risk scores are always computed from the same underlying model, guaranteeing mathematical consistency&#x2014;a property termed unified risk coupling that is absent from all prior women-safety navigation systems.'))
parts.append(body('Additional safety features include an SOS emergency alert module with GPS coordinate dispatch to pre-registered emergency contacts, voice-activated emergency triggers, safe and unsafe zone delineation based on historical crime density, and a community-sourced incident reporting interface. The system was evaluated through functional testing, performance benchmarking, and user acceptance testing, demonstrating sub-second heatmap regeneration, reliable SOS dispatch, and measurably improved route safety scores compared to distance-optimal routing.'))
parts.append(body('SafeHer aligns with United Nations Sustainable Development Goal 5 (Gender Equality) and SDG 11 (Sustainable Cities and Communities) by providing women with a data-driven, accessible, and real-time safety tool for urban navigation. This report documents the system design, machine learning methodology, backend architecture, frontend implementation, sprint-based development process, evaluation results, and directions for future enhancement including IoT wearable integration and multi-city generalisation.'))
parts.append(empty_para())
parts.append(body([run('Keywords: ', bold=True), run('Women Safety, AI, LightGBM, Crime Prediction, Safe Navigation, SOS Alert, GPS Tracking, Real-Time Heatmap, Flask, React.js, Google Maps API')]))

# Section 4 break
parts.append(section_break('rId16', top='1580', right='400', bottom='280', left='780', w='11910', h='16840'))

# ============================================================
# TABLE OF CONTENTS + LISTS + ABBREVIATIONS (Section 5 - footer rId18)
# ============================================================
parts.append(empty_para())
parts.append(bold_center('TABLE OF CONTENTS', sz=28))
parts.append(empty_para())

toc_entries = [
    ('Abstract', 'v'),
    ('Table of Contents', 'vi'),
    ('List of Figures', 'vii'),
    ('List of Tables', 'viii'),
    ('Abbreviations', 'ix'),
    ('CHAPTER 1: INTRODUCTION', '1'),
    ('    1.1  Introduction to the Project', '2'),
    ('    1.2  Problem Statement and Description', '4'),
    ('    1.3  Motivation', '5'),
    ('    1.4  Sustainable Development Goals', '6'),
    ('CHAPTER 2: LITERATURE SURVEY', '7'),
    ('    2.1  Overview of the Research Area', '8'),
    ('    2.2  Existing Systems and Research', '9'),
    ('    2.3  Research Gaps', '12'),
    ('    2.4  Research Objectives', '13'),
    ('    2.5  Product Backlog (User Stories)', '14'),
    ('    2.6  Plan of Action (Project Roadmap)', '16'),
    ('CHAPTER 3: SPRINT PLANNING AND EXECUTION', '18'),
    ('    3.1  Sprint I - ML Pipeline and Risk Model', '19'),
    ('    3.2  Sprint II - Backend API and Frontend', '27'),
    ('CHAPTER 6: RESULTS AND DISCUSSIONS', '35'),
    ('    6.1  Performance Evaluation', '36'),
    ('    6.2  Testing and Comparisons', '40'),
    ('CHAPTER 7: CONCLUSION AND FUTURE ENHANCEMENT', '43'),
    ('References', '45'),
    ('Appendix A - Code Samples', '48'),
    ('Appendix B - Publications', '50'),
]
for entry, page in toc_entries:
    is_bold = entry.startswith('CHAPTER') or entry in ('Abstract', 'Table of Contents', 'List of Figures', 'List of Tables', 'Abbreviations', 'References', 'Appendix A - Code Samples', 'Appendix B - Publications')
    parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9000"/></w:tabs></w:pPr><w:r><w:rPr>{"<w:b/><w:bCs/>" if is_bold else ""}<w:sz w:val="24"/></w:rPr>{t(entry)}</w:r><w:r><w:rPr><w:sz w:val="24"/></w:rPr><w:tab/>{t(page)}</w:r></w:p>')

parts.append(page_break())
parts.append(bold_center('LIST OF FIGURES', sz=28))
parts.append(empty_para())
figures = [
    ('1.1', 'SafeHer System Overview Diagram', '3'),
    ('1.2', 'Sustainable Development Goals Alignment', '6'),
    ('2.1', 'Comparison of Existing Safety Applications', '10'),
    ('2.2', 'Project Roadmap / Gantt Chart', '17'),
    ('3.1', 'ML Pipeline Architecture', '21'),
    ('3.2', 'Severity Class Distribution (Class Imbalance)', '22'),
    ('3.3', 'Crime Danger Index Formula and Distribution', '23'),
    ('3.4', 'LightGBM Feature Importance Chart', '25'),
    ('3.5', 'Temporal Multiplier Heatmap (24 x 7 Grid)', '26'),
    ('3.6', 'SafeHer System Architecture Diagram', '29'),
    ('3.7', 'Database Entity Relationship Diagram', '31'),
    ('3.8', 'API Flow Diagram', '32'),
    ('3.9', 'Risk Heatmap UI Screenshot', '33'),
    ('3.10', 'Safe Route Recommendation UI Screenshot', '34'),
    ('6.1', 'Model Performance Comparison - R2 and MAE', '37'),
    ('6.2', 'Grid Generation Speed - LightGBM vs CNN-LSTM', '38'),
    ('6.3', 'SOS Alert Flow Testing Results', '41'),
    ('6.4', 'User Acceptance Testing Results', '42'),
]
parts.append(make_table(['Fig. No.', 'Title', 'Page No.'], figures, [1200, 6800, 1000]))

parts.append(page_break())
parts.append(bold_center('LIST OF TABLES', sz=28))
parts.append(empty_para())
tables_list = [
    ('2.1', 'Comparison of Existing Women Safety Applications', '11'),
    ('2.2', 'Product Backlog - User Stories', '15'),
    ('3.1', 'Sprint I - Objectives and Deliverables', '20'),
    ('3.2', 'Dataset Summary Statistics', '22'),
    ('3.3', 'Feature Engineering Summary', '24'),
    ('3.4', 'Sprint II - Objectives and Deliverables', '28'),
    ('3.5', 'API Endpoint Reference', '32'),
    ('6.1', 'Spatial Risk Model Comparison (Table I)', '37'),
    ('6.2', 'System Timing Evaluation (Table II)', '39'),
    ('6.3', 'Functional Test Cases and Results', '41'),
    ('6.4', 'User Acceptance Testing Scores', '42'),
]
parts.append(make_table(['Table No.', 'Title', 'Page No.'], tables_list, [1200, 6800, 1000]))

parts.append(page_break())
parts.append(bold_center('ABBREVIATIONS', sz=28))
parts.append(empty_para())
abbrevs = [
    ('AI', 'Artificial Intelligence'), ('API', 'Application Programming Interface'),
    ('CDI', 'Crime Danger Index'), ('CNN', 'Convolutional Neural Network'),
    ('CSS', 'Cascading Style Sheet'), ('CSV', 'Comma-Separated Values'),
    ('DB', 'Database'), ('EDA', 'Exploratory Data Analysis'),
    ('GPS', 'Global Positioning System'), ('GBM', 'Gradient Boosting Machine'),
    ('HTML', 'Hyper Text Markup Language'), ('HTTP', 'Hyper Text Transfer Protocol'),
    ('JSON', 'JavaScript Object Notation'), ('JS', 'JavaScript'),
    ('LightGBM', 'Light Gradient Boosting Machine'), ('MAE', 'Mean Absolute Error'),
    ('ML', 'Machine Learning'), ('R2', 'Coefficient of Determination'),
    ('REST', 'Representational State Transfer'), ('RF', 'Random Forest'),
    ('SDG', 'Sustainable Development Goal'), ('SOS', 'Save Our Souls (Emergency Signal)'),
    ('SQL', 'Structured Query Language'), ('UI', 'User Interface'),
    ('URL', 'Uniform Resource Locator'), ('XGBoost', 'Extreme Gradient Boosting'),
]
parts.append(make_table(['Abbreviation', 'Full Form'], abbrevs, [3000, 6000]))

# Section 5 break
parts.append(section_break('rId18', top='1260', right='400', bottom='280', left='780', w='11910', h='16840'))

# ============================================================
# CHAPTERS 1 - 6 (Section 6 - footer rId21)
# ============================================================

# CHAPTER 1
parts.append(heading1('CHAPTER 1'))
parts.append(heading1('INTRODUCTION'))
parts.append(empty_para())
parts.append(heading2('1.1 Introduction to the Project'))
parts.append(body('In urban environments across the world, personal safety - particularly for women - remains a profoundly underserved concern. Despite significant technological advances in navigation, communication, and data analytics, mainstream mapping and transportation platforms continue to optimise routes exclusively for travel time and shortest distance. No consideration is given to the relative safety of a path, the historical crime profile of a neighbourhood, or the time-of-day variation in criminal activity. This fundamental gap creates a measurable disadvantage for women navigating public spaces, particularly after dark.'))
parts.append(body('SafeHer is an AI-powered, real-time women safety and emergency response system designed to address this gap through a comprehensive multi-modal framework. The system combines machine learning-driven crime risk prediction, GPS-based live location tracking, SOS emergency alert dispatch, voice-activated emergency triggers, and intelligent safe-route recommendation - all accessible through an intuitive web and mobile interface built on React.js and integrated with the Google Maps JavaScript API.'))
parts.append(body('At the core of SafeHer lies a two-component risk model: a LightGBM regressor trained on 8.4 million historical crime incidents from the City of Chicago (2001-2025) predicts spatial danger scores per 200-metre grid cell, while a 168-slot empirical temporal multiplier captures how crime risk varies by hour and day of week. Together, these components power a live heatmap that updates in under one second as users move the time slider - a capability that no prior women-safety system has demonstrated in the published literature.'))
parts.append(body("The system's most architecturally significant property is its unified risk coupling: both the visual heatmap and the route-scoring engine are powered by the exact same model call. This guarantees that the green, amber, or red colour a user sees on the heatmap for any neighbourhood is mathematically identical to the risk contribution of a route passing through that neighbourhood. This consistency - absent from all prior systems - ensures that the system's safety recommendations are always grounded in the same empirical evidence the user can visually inspect."))
parts.append(body('[Figure 1.1: SafeHer System Overview - Components and Data Flow]'))

parts.append(heading2('1.2 Problem Statement and Description'))
parts.append(body('Women face disproportionate levels of street harassment, assault, and violence in public spaces, particularly during nighttime travel. A 2020 study by Vera-Gray and Kelly [1] demonstrated that fear of crime significantly restricts women\'s mobility, limits their participation in public life, and induces route modifications that prioritise perceived safety over efficiency. Despite this well-documented need, the technology industry has largely failed to incorporate safety as a first-class routing criterion.'))
parts.append(body('The problem has three computable dimensions. First, existing navigation applications have no mechanism for crime-risk-aware routing; they treat all streets as equally safe at all times. Second, existing safety-focused applications - such as Safetipin and similar crowdsourced platforms - rely on subjective user audits that are geographically sparse, temporally static, and dependent on sustained community participation, making them unreliable for real-time navigation decisions. Third, when academic systems do incorporate crime data, they typically use static, time-averaged risk maps that do not reflect the dramatic intra-day variation in crime patterns.'))
parts.append(body('SafeHer addresses all three dimensions: it integrates real crime data at 200-metre spatial resolution with hourly temporal granularity, provides consistent risk scoring across both map visualisation and route recommendation, and includes emergency response capabilities that existing systems entirely lack.'))

parts.append(heading2('1.3 Motivation'))
parts.append(body('The motivation for SafeHer emerges from three converging imperatives: social necessity, technological opportunity, and academic originality.'))
parts.append(body('From the social perspective, published statistics paint a sobering picture. According to the National Crime Records Bureau (NCRB) of India, crimes against women increased by 15.3% between 2019 and 2021. In the United States, the FBI Uniform Crime Reporting (UCR) data indicates that violent crime disproportionately affects women in public spaces during evening and nighttime hours. Yet the tools available to women for real-time safety decision-making remain primitive: most rely on manual reporting or subjective community ratings, offer no temporal sensitivity, and provide no integration between what is displayed on a map and what is recommended as a route.'))
parts.append(body('From the technological perspective, the convergence of open crime datasets (such as Chicago\'s publicly available 8.4 million-incident dataset), lightweight gradient-boosting models capable of sub-second inference, and modern web APIs for mapping and location services creates an unprecedented opportunity to build a genuinely useful safety tool at low cost and high quality.'))
parts.append(body('From the academic perspective, SafeHer makes five novel contributions: (1) a Crime Danger Index (CDI) percentile target; (2) a two-component risk architecture; (3) unified risk coupling between heatmap and route scorer; (4) 13-feature spatial engineering from public data alone; and (5) a dynamic temporal heatmap that changes visually hour-by-hour.'))

parts.append(heading2('1.4 Sustainable Development Goal (SDG) Alignment'))
parts.append(body('SafeHer directly addresses the United Nations Sustainable Development Goals 5 and 11, and contributes indirectly to SDG 3 and SDG 16.'))
parts.append(body([run('SDG 5 - Gender Equality: ', bold=True), run('Target 5.2 mandates the elimination of all forms of violence against women in the public sphere. SafeHer directly serves this target by providing women with actionable, data-driven information about the relative safety of urban spaces at different times of day.')]))
parts.append(body([run('SDG 11 - Sustainable Cities and Communities: ', bold=True), run('Target 11.7 calls for universal access to safe, inclusive, and accessible public spaces, particularly for women. SafeHer contributes to this target by making real-time crime risk information accessible through a standard web browser.')]))
parts.append(body([run('SDG 3 - Good Health and Well-Being: ', bold=True), run('By reducing the number of situations in which women are exposed to dangerous environments unknowingly, SafeHer contributes to physical safety and mental health outcomes associated with reduced fear and anxiety during urban navigation.')]))
parts.append(body([run('SDG 16 - Peace, Justice and Strong Institutions: ', bold=True), run("SafeHer's use of officially reported crime data and its presentation of risk as a relative percentile aligns with principles of fairness and evidence-based public safety.")]))
parts.append(body('[Figure 1.2: SDG Alignment Diagram for SafeHer]'))

# CHAPTER 2
parts.append(page_break())
parts.append(heading1('CHAPTER 2'))
parts.append(heading1('LITERATURE SURVEY'))
parts.append(empty_para())
parts.append(heading2('2.1 Overview of the Research Area'))
parts.append(body('The intersection of artificial intelligence, geographic information systems (GIS), and personal safety represents a rapidly growing research domain. Three sub-fields are directly relevant to SafeHer: (i) machine learning-based crime prediction and spatial risk modelling; (ii) safety-aware navigation and route recommendation; and (iii) real-time emergency response systems.'))
parts.append(body('Crime prediction using machine learning has a substantial academic history. Early approaches relied on kernel density estimation (KDE) [2] to produce static hotspot maps from historical incident data. More recent work has applied ensemble methods - including Random Forest [3] and gradient-boosting models [4] - to tabular crime data, demonstrating substantially improved prediction accuracy when spatial features such as community area and distance to police stations are incorporated.'))
parts.append(body('Safety-aware navigation represents a smaller but growing sub-field. SafePath [6] constructs a graph of city streets with crime-weighted edges and applies Dijkstra\'s algorithm to find safer paths. CrimeTravel [7] extends this with multi-objective optimisation balancing safety against travel time. Both systems suffer from two structural limitations: their risk models are time-invariant, and their map visualisation and route-scoring components use independently computed risk estimates.'))
parts.append(body('Emergency response systems for women have largely focused on SOS alerting, GPS tracking, and contact notification rather than risk prediction. Applications such as Safetipin [9], bSafe, and Nimb operate in this space. SafeHer bridges both tracks - integrating real-time emergency response with AI-driven risk prediction and route recommendation in a single unified system.'))

parts.append(heading2('2.2 Existing Systems and Research'))
parts.append(body([run('Table 2.1: Comparison of Existing Women Safety Applications and Research Systems', bold=True)]))
parts.append(empty_para())
comparison_table = make_table(
    ['System', 'Approach', 'Limitations', 'SafeHer Advantage'],
    [
        ['Safetipin', 'Crowdsourced safety audits + POI data', 'Subjective, sparse, no real-time update', 'Uses 8.4M official police records; objective and dense'],
        ['SafePath [6]', 'Crime-weighted graph + Dijkstra routing', 'Static risk; route and heatmap decoupled', 'Dynamic temporal risk; unified risk coupling'],
        ['CrimeTravel [7]', 'Multi-objective optimisation (safety + time)', 'No temporal variation; no heatmap', '168-slot temporal multiplier; live heatmap'],
        ['WalkSafe [8]', 'Smartphone sensors for pedestrian safety', 'No spatial crime density model', 'LightGBM spatial regressor; 200m grid cells'],
        ['bSafe / Nimb', 'SOS button + live GPS share', 'No risk prediction or routing', 'Full SOS + routing + heatmap in one system'],
        ['KDE Hotspot [2]', 'Kernel density estimation on incident data', 'Static; no temporal variation; no routing', 'Dynamic hourly heatmap; route scoring'],
        ['CNN-LSTM [5]', 'Deep learning spatial-temporal model', '~90s per heatmap; needs GPU', 'LightGBM: <1s; runs on CPU; 105x faster'],
        ['Google Maps', 'Time/distance optimal routing', 'No safety consideration whatsoever', 'Safety-ranked routes from same model as heatmap'],
    ],
    [1800, 2400, 2500, 2300]
)
parts.append(comparison_table)
parts.append(body('[Figure 2.1: Comparison of Existing Safety Applications - Feature Matrix]'))

parts.append(heading2('2.3 Research Gaps Identified from Literature'))
parts.append(body([run('Gap 1 - Temporal Static Risk Models: ', bold=True), run('All existing crime-aware navigation systems use time-averaged risk scores. None account for the fact that the same location can be safe at 9AM and genuinely dangerous at 11PM. The temporal multiplier in SafeHer, covering 168 time slots (24 hours x 7 days), directly addresses this gap.')]))
parts.append(body([run('Gap 2 - Inconsistency Between Heatmap and Route Scorer: ', bold=True), run('Existing systems that display a risk heatmap and also recommend routes compute these using separate, independently-tuned risk estimates. SafeHer introduces unified risk coupling as a first-class design property.')]))
parts.append(body([run('Gap 3 - Scalability of Deep Learning Approaches: ', bold=True), run('CNN-LSTM models achieve strong predictive accuracy but require approximately 90 seconds to regenerate a city-wide heatmap at 200-metre resolution, making them incompatible with real-time interactive use.')]))
parts.append(body([run('Gap 4 - Class Imbalance in Crime Severity Prediction: ', bold=True), run('Per-incident severity classification is ill-posed because the same location at the same time can produce both low-severity and high-severity incidents. The CDI percentile target resolves this.')]))
parts.append(body([run('Gap 5 - Separation of Safety Navigation and Emergency Response: ', bold=True), run('No existing system combines AI-driven risk prediction, route recommendation, and SOS emergency alerting in a single platform.')]))

parts.append(heading2('2.4 Research Objectives'))
parts.append(body('Based on the identified gaps, the following research objectives were defined:'))
parts.append(bullet('Design a crime-risk target variable (CDI percentile) that is learnable, uniformly distributed, and free from class imbalance.'))
parts.append(bullet('Train a spatial risk model achieving R2 >= 0.99 on held-out 200-metre grid cells using a 13-feature engineering pipeline.'))
parts.append(bullet('Construct a temporal multiplier that captures meaningful intra-day risk variation across 168 (hour, day-of-week) time slots without retraining the spatial model.'))
parts.append(bullet('Implement a unified risk grid architecture that serves both the dynamic heatmap and the route-scoring pipeline from an identical risk computation.'))
parts.append(bullet('Build a real-time SOS emergency alert module that dispatches GPS coordinates to pre-registered emergency contacts within five seconds.'))
parts.append(bullet('Develop a voice-activated emergency trigger enabling hands-free SOS dispatch.'))
parts.append(bullet('Deliver a React.js + Google Maps interface with sub-second heatmap response and interactive temporal control.'))

parts.append(heading2('2.5 Product Backlog - Key User Stories with Desired Outcomes'))
parts.append(body([run('Table 2.2: Product Backlog - User Stories for SafeHer', bold=True)]))
parts.append(empty_para())
backlog_table = make_table(
    ['ID', 'As a...', 'I want to...', 'Priority', 'Sprint'],
    [
        ['US-01', 'user', 'view a real-time crime risk heatmap of my city that updates as I change the hour', 'Critical', 'Sprint I'],
        ['US-02', 'user', 'find the safest route between two locations at a given time of day', 'Critical', 'Sprint II'],
        ['US-03', 'user', 'trigger an SOS alert that sends my GPS location to emergency contacts instantly', 'Critical', 'Sprint II'],
        ['US-04', 'user', 'activate emergency mode by voice without unlocking my phone', 'High', 'Sprint II'],
        ['US-05', 'user', 'register emergency contacts who receive my location during an SOS', 'High', 'Sprint II'],
        ['US-06', 'user', 'see a colour-coded map of safe and unsafe zones around my current location', 'High', 'Sprint I'],
        ['US-07', 'user', 'compare multiple route options with their respective safety scores', 'High', 'Sprint II'],
        ['US-08', 'user', 'report a safety incident at my current location with one click', 'Medium', 'Sprint II'],
        ['US-09', 'administrator', 'view aggregated incident reports and update the crime dataset', 'Medium', 'Sprint II'],
        ['US-10', 'researcher', 'access the model performance metrics and system evaluation tables', 'Low', 'Sprint I'],
    ],
    [700, 1500, 3500, 1200, 1200]
)
parts.append(backlog_table)

parts.append(heading2('2.6 Plan of Action (Project Roadmap)'))
parts.append(body('The development of SafeHer was organised into four sequential phases aligned with the project\'s sprint structure. The roadmap follows an Agile Scrum methodology with two two-week sprints forming the core of the implementation phase.'))
parts.append(body([run('Phase 1 - Data Acquisition and EDA (Week 1): ', bold=True), run('Download the Chicago Crimes Dataset (8.4 million incidents, 2001-2025) and execute the EDA pipeline to identify class imbalance, geographic outliers, and temporal patterns.')]))
parts.append(body([run('Phase 2 - ML Pipeline (Week 2, Sprint I): ', bold=True), run('Execute preprocess.py (feature engineering: 13 features per incident, 200-metre grid construction), train.py (CDI target construction, LightGBM training, temporal lookup construction), and evaluate.py to generate evaluation tables.')]))
parts.append(body([run('Phase 3 - Backend and Frontend (Week 3, Sprint II): ', bold=True), run('Implement Flask REST API endpoints (heatmap, safe-route, SOS, emergency contacts) and React.js frontend components (HeatMap, RouteMap, HourSlider, SOS Panel, User Profile).')]))
parts.append(body([run('Phase 4 - Paper, Demo, and Documentation (Week 4): ', bold=True), run('Write the IEEE Access manuscript, generate all figures and tables, prepare the demo script, write the README and project report.')]))
parts.append(body('[Figure 2.2: Project Roadmap / Gantt Chart - 4 Phases Over 4 Weeks]'))

# CHAPTER 3
parts.append(page_break())
parts.append(heading1('CHAPTER 3'))
parts.append(heading1('SPRINT PLANNING AND EXECUTION METHODOLOGY'))
parts.append(empty_para())
parts.append(body('The development of SafeHer followed an Agile Scrum methodology structured around two formal sprints, each comprising two weeks of iterative development, daily stand-ups, and a sprint retrospective. This chapter documents the objectives, user stories, functional design, architecture, implementation details, and retrospective findings for each sprint.'))

parts.append(heading2('3.1 SPRINT I - Machine Learning Pipeline and Risk Model'))
parts.append(heading3('3.1.1 Objectives with User Stories of Sprint I'))
parts.append(body([run('Table 3.1: Sprint I - Objectives, User Stories, and Deliverables', bold=True)]))
parts.append(empty_para())
sprint1_table = make_table(
    ['ID', 'Objective / Task', 'Status', 'Deliverable'],
    [
        ['SP1-01', 'Download Chicago Crimes Dataset (8.4M rows) and Police Stations CSV', 'Done', 'chicago_crimes.csv, police_stations.csv'],
        ['SP1-02', 'Run EDA pipeline (8 sections: imbalance, temporal, geographic, etc.)', 'Done', 'eda_report.txt'],
        ['SP1-03', 'Feature engineering: 13 features, 200m grid, rolling 7-day rate', 'Done', 'chicago_processed.csv'],
        ['SP1-04', 'Build Crime Danger Index (CDI) target with percentile rank', 'Done', 'base_risk column in training data'],
        ['SP1-05', 'Train LightGBM regressor with early stopping (1000 estimators)', 'Done', 'lgbm_model.pkl'],
        ['SP1-06', 'Build temporal multiplier lookup (168 slots, violent crimes)', 'Done', 'temporal_lookup.pkl'],
        ['SP1-07', 'Build density lookup (grid_lat, grid_lon -> crime_count)', 'Done', 'density_lookup.pkl'],
        ['SP1-08', 'Train baseline models: Random Forest, XGBoost', 'Done', 'Baseline metrics in Table 1'],
        ['SP1-09', 'Generate paper Table 1 (spatial comparison) and Table 2 (timing)', 'Done', 'paper_tables.csv'],
        ['SP1-10', 'Implement heatmap + safe-zone visualisation preview', 'Done', 'Preview plots in EDA report'],
    ],
    [800, 3800, 1000, 3400]
)
parts.append(sprint1_table)

parts.append(heading3('3.1.2 Functional Document'))
parts.append(body('Sprint I encompasses the complete machine learning pipeline for SafeHer. The pipeline consists of three sequential Python scripts: eda.py, preprocess.py, and train.py.'))
parts.append(body([run('A. Exploratory Data Analysis (eda.py)', bold=True)]))
parts.append(body('The EDA script processes the raw Chicago Crimes CSV and produces an eight-section analysis report. The most significant findings were: (1) a 58.6x class imbalance between Severity 1 (narcotics, vandalism: 33.8%) and Severity 5 (homicide, sexual assault: 0.58%); (2) an artificial midnight spike caused by Chicago Police Department\'s convention of recording incidents with unknown reporting times as 00:00; (3) an initial grid resolution bug where GRID_MULT=100 produced only 747 cells instead of the correct 14,129 at GRID_MULT=500; and (4) geographic outliers beyond Chicago\'s bounding box requiring filtering.'))
parts.append(empty_para())
parts.append(body([run('Table 3.2: Chicago Crimes Dataset - Summary Statistics After EDA', bold=True)]))
parts.append(empty_para())
dataset_table = make_table(
    ['Attribute', 'Value'],
    [
        ['Raw rows', '8,514,784'],
        ['Rows after bounding-box filter', '8,406,015'],
        ['Date range', 'January 2001 - December 2025'],
        ['Total raw columns', '22'],
        ['Engineered features', '13 (+ 1 target)'],
        ['Unique crime types', '34'],
        ['Grid cells at 200m resolution (GRID_MULT=500)', '14,129'],
        ['Community areas represented', '78'],
        ['Police districts', '25'],
        ['Class imbalance ratio (Severity 1 : Severity 5)', '58.6x'],
        ['Peak crime hour', '00:00 (data-entry artifact); true peak: 10PM-1AM'],
    ],
    [5000, 4000]
)
parts.append(dataset_table)

parts.append(empty_para())
parts.append(body([run('B. Feature Engineering (preprocess.py)', bold=True)]))
parts.append(body('The preprocessing script engineers 13 features from the raw incident data across five categories. Temporal features (hour, day_of_week, month, is_night, is_weekend) are extracted from the Date column. Crime characterisation features (severity, location_type, is_domestic) are mapped from categorical columns. Zone features (community_area, police_district) provide spatial context. Density features (crime_count, rolling_7day) encode historical frequency. The external feature distance_to_police is computed via a KD-tree nearest-neighbour search over 25 Chicago police station coordinates.'))
parts.append(empty_para())
parts.append(body([run('Table 3.3: Feature Engineering Summary - 13 Features Across 5 Categories', bold=True)]))
parts.append(empty_para())
feat_table = make_table(
    ['Category', 'Feature', 'Derivation / Notes'],
    [
        ['Temporal', 'hour (0-23)', 'dt.hour from parsed Date column'],
        ['Temporal', 'day_of_week (0-6)', 'dt.dayofweek; 0=Mon, 6=Sun'],
        ['Temporal', 'month (1-12)', 'dt.month'],
        ['Temporal', 'is_night (0/1)', '1 if hour >= 21 OR hour <= 5; validated by EDA'],
        ['Temporal', 'is_weekend (0/1)', '1 if day_of_week >= 5 (Sat, Sun)'],
        ['Crime', 'severity (1-5)', 'Mapped from Primary Type; 34 crime types -> 5 levels'],
        ['Crime', 'location_type (1-6)', 'Ordinal: alley=6, parking=5, transit=4, street=3, residence=1'],
        ['Crime', 'is_domestic (0/1)', 'Direct cast of Domestic column; 17.3% of incidents'],
        ['Zone', 'community_area (0-77)', 'From Community Area; NaN -> 0 (not dropped)'],
        ['Zone', 'police_district (0-25)', 'From District; 47 NaN rows -> 0'],
        ['Density', 'crime_count (int)', 'All-time crime count per 200m grid cell; max: 17,575'],
        ['Density', 'rolling_7day (float)', '7-day rolling crime count per cell; mean: 2.73'],
        ['External', 'distance_to_police (km)', 'KD-tree NN to 25 stations; mean: 2.32 km, max: 19.46 km'],
    ],
    [1500, 2500, 5000]
)
parts.append(feat_table)

parts.append(empty_para())
parts.append(body([run('C. Model Training and CDI Target (train.py)', bold=True)]))
parts.append(body('The training script implements the two-component risk architecture. For the spatial component, incidents are aggregated to one row per grid cell (14,129 rows), and the Crime Danger Index (CDI) is computed as: CDI(cell) = violent_rate(cell) x log(1 + crime_count(cell)), where violent_rate is the fraction of incidents with severity >= 3. CDI is then converted to a percentile rank, yielding a uniform [0, 1] distribution with exactly 30% of cells exceeding 0.7.'))
parts.append(body('For the temporal component, a 168-slot lookup table is constructed from violent crime rates: T(hour, day) = count_violent(hour, day) / mean(count_violent). The multiplier ranges from 0.336 (Monday-Thursday, 4-5AM) to 1.507 (Sunday midnight), representing a 4.5x dynamic range in expected violent crime frequency.'))
parts.append(body('[Figure 3.1: ML Pipeline Architecture - From Raw Data to Deployed Model]'))
parts.append(body('[Figure 3.2: Severity Class Distribution - 58.6x Imbalance Confirming CDI Necessity]'))
parts.append(body('[Figure 3.3: Crime Danger Index Formula and Uniform Distribution]'))

parts.append(heading3('3.1.3 Architecture Document'))
parts.append(body('The machine learning architecture of SafeHer separates risk into two orthogonal components with fundamentally different statistical properties. Spatial risk is stable over weeks and can be learned by a supervised model from historical data. Temporal variation is better captured as a direct empirical observation from the dataset rather than as a latent variable requiring ML to estimate.'))
parts.append(body('The LightGBM regressor is configured with 1,000 estimators, learning rate 0.02, maximum depth 8, number of leaves 63, minimum child samples 3, early stopping after 80 rounds, and column/subsample ratio of 0.8. Training on 11,303 cells (80% split) completes in approximately 6.4 seconds on a modern laptop.'))
parts.append(body('The combined risk formula applied at inference is: risk(cell, hour, day) = clip(spatial_risk(cell) x temporal_multiplier(hour, day), 0, 1).'))
parts.append(body('[Figure 3.4: LightGBM Feature Importance Chart - Split-Based Scores]'))
parts.append(body('[Figure 3.5: Temporal Multiplier Grid (24 Hours x 7 Days)]'))

parts.append(heading3('3.1.4 Outcome of Objectives - Result Analysis'))
parts.append(body('Sprint I achieved all ten defined objectives. The key quantitative outcomes are:'))
parts.append(bullet('LightGBM spatial model: MAE = 0.0030, R2 = 0.9997, HR-Precision = 0.9920, HR-Recall = 0.9954, inference time = 0.03s per 10,000 cells.'))
parts.append(bullet('Random Forest baseline: MAE = 0.0022, R2 = 0.9997, HR-Precision = 0.9988, HR-Recall = 0.9954.'))
parts.append(bullet('XGBoost baseline: MAE = 0.0040, R2 = 0.9995, HR-Precision = 1.0000, HR-Recall = 0.9943.'))
parts.append(bullet('Temporal multiplier: 168 slots, multiplier range 0.336 -> 1.507, top dangerous slot: Sunday 00:00 (1.507x).'))
parts.append(bullet('High-risk cell count: 50 at 6AM (multiplier 0.336x), rising to 800 at midnight (multiplier 1.507x) - a 16x increase from temporal variation alone.'))
parts.append(bullet('Four model artifacts saved: lgbm_model.pkl, density_lookup.pkl, temporal_lookup.pkl, risk_scaler.pkl.'))

parts.append(heading3('3.1.5 Sprint I Retrospective'))
parts.append(body([run('What went well: ', bold=True), run('The CDI percentile rank target resolved the fundamental ill-posedness of per-incident severity classification, producing a dramatic improvement in R2 from < 0.17 (naive targets) to 0.9997. The GRID_MULT=500 correction was identified by EDA before training, avoiding a critical architecture error.')]))
parts.append(body([run('What could be improved: ', bold=True), run('The rolling 7-day computation required 3-5 minutes on 8.4 million rows due to the per-cell groupby loop. A vectorised approach using pandas DatetimeIndex resampling would reduce this to under 30 seconds.')]))
parts.append(body([run('Action items for Sprint II: ', bold=True), run('Implement Flask API endpoints using the artifacts from Sprint I. Build the React frontend with shared hour/day state. Integrate Google Maps HeatmapLayer and Directions API. Implement the SOS emergency alert module.')]))

parts.append(heading2('3.2 SPRINT II - Backend API, Frontend, and Emergency Response'))
parts.append(heading3('3.2.1 Objectives with User Stories of Sprint II'))
parts.append(body([run('Table 3.4: Sprint II - Objectives, User Stories, and Deliverables', bold=True)]))
parts.append(empty_para())
sprint2_table = make_table(
    ['ID', 'Objective / Task', 'Status', 'Deliverable'],
    [
        ['SP2-01', 'Implement risk_grid.py - shared two-component risk engine', 'Done', 'risk_grid.py with generate_risk_grid() and score_polyline_points()'],
        ['SP2-02', 'Implement /api/heatmap Flask endpoint', 'Done', 'routes_heatmap.py; JSON {lat, lon, risk}'],
        ['SP2-03', 'Implement /api/safe-route Flask endpoint with Directions API', 'Done', 'routes_saferoute.py; routes sorted by avg_risk'],
        ['SP2-04', 'Implement SOS alert module with GPS dispatch', 'Done', '/api/sos endpoint; email + SMS to contacts'],
        ['SP2-05', 'Implement emergency contact CRUD API', 'Done', '/api/contacts endpoints'],
        ['SP2-06', 'Build App.jsx with shared hour/day state', 'Done', 'React root with HeatMap + RouteMap tabs'],
        ['SP2-07', 'Build HeatMap.jsx with Google Maps HeatmapLayer', 'Done', 'Dynamic heatmap re-fetching on slider change'],
        ['SP2-08', 'Build RouteMap.jsx with coloured polylines and risk cards', 'Done', 'Three route alternatives; sorted safest-first'],
        ['SP2-09', 'Build HourSlider.jsx with gradient track and quick-jump buttons', 'Done', '24-hour slider with risk-colour gradient'],
        ['SP2-10', 'Integrate Google Places Autocomplete for route inputs', 'Done', 'Origin/destination with Chicago-bound autocomplete'],
        ['SP2-11', 'Voice-activated SOS trigger using Web Speech API', 'Done', "Keyword detection: 'help' / 'SOS'"],
        ['SP2-12', 'Implement incident reporting form with GPS tagging', 'Done', 'POST /api/incidents with category and description'],
    ],
    [800, 3800, 1000, 3400]
)
parts.append(sprint2_table)

parts.append(heading3('3.2.2 Functional Document'))
parts.append(body([run('A. Backend Architecture (Flask API)', bold=True)]))
parts.append(body('The Flask backend exposes a RESTful API with two primary data endpoints and three auxiliary endpoints. The most architecturally significant design decision is the shared risk engine: both /api/heatmap and /api/safe-route call the same generate_risk_grid() function defined in risk_grid.py. This function loads the LightGBM model, density lookup, and temporal lookup once at process startup, ensuring zero cold-start latency on subsequent requests.'))
parts.append(body('The /api/heatmap endpoint accepts hour (0-23) and day (0-6) query parameters, calls generate_risk_grid(), filters out zero-risk cells (reducing JSON payload by approximately 60%), and returns a list of {lat, lon, risk} objects. The /api/safe-route endpoint fetches up to three alternative driving routes from the Google Directions API, decodes each route\'s overview polyline, samples every fifth waypoint to reduce scoring overhead, and calls score_polyline_points() with the same two-component formula.'))
parts.append(empty_para())
parts.append(body([run('Table 3.5: SafeHer REST API Endpoint Reference', bold=True)]))
parts.append(empty_para())
api_table = make_table(
    ['Endpoint', 'Method', 'Parameters', 'Response'],
    [
        ['/api/heatmap', 'GET', 'hour (0-23), day (0-6)', '[{lat, lon, risk}] - filtered (risk > 0)'],
        ['/api/safe-route', 'GET', 'origin, destination, hour, day', 'Routes sorted by avg_risk; {polyline, label, color, duration, distance}'],
        ['/api/sos', 'POST', 'latitude, longitude, user_id', 'Dispatches GPS to all registered emergency contacts'],
        ['/api/contacts', 'GET/POST/DELETE', 'user_id, contact details', 'CRUD for emergency contact list'],
        ['/api/incidents', 'POST', 'latitude, longitude, category, description', 'Creates user-submitted incident report'],
        ['/api/health', 'GET', 'None', '{status: ok, service: SafeHer API}'],
    ],
    [2000, 1000, 2500, 3500]
)
parts.append(api_table)

parts.append(heading3('3.2.3 Architecture Document'))
parts.append(body([run('A. Full System Architecture', bold=True)]))
parts.append(body('The SafeHer system is structured as a three-tier architecture: a React.js + Google Maps frontend (presentation tier), a Flask REST API (application tier), and a combination of serialised ML artifacts (LightGBM pickle files) and a MySQL database for user data (data tier). The application tier is the most critical: it is stateless with respect to the risk model (all risk computation uses in-memory artifacts loaded at startup) and stateful with respect to user accounts, emergency contacts, and incident reports (stored in MySQL).'))
parts.append(body('[Figure 3.6: SafeHer Full System Architecture - Three-Tier Diagram]'))
parts.append(body([run('B. Database Schema', bold=True)]))
parts.append(body('The MySQL database (safeher_db) contains four primary tables: users (user_id, email, password_hash, name, created_at), emergency_contacts (contact_id, user_id FK, name, phone, email, relation), incidents (incident_id, user_id FK, latitude, longitude, category, description, timestamp), and sos_log (log_id, user_id FK, latitude, longitude, contacts_notified, timestamp).'))
parts.append(body('[Figure 3.7: Database Entity Relationship Diagram (ER Diagram)]'))
parts.append(body('[Figure 3.8: API Flow Diagram - Heatmap and Safe-Route Request Lifecycle]'))

parts.append(heading3('3.2.4 Outcome of Objectives - Result Analysis'))
parts.append(body('Sprint II successfully delivered all twelve objectives. The primary outcomes are:'))
parts.append(bullet('The Flask API runs reliably at http://localhost:5000 with all six endpoints functional.'))
parts.append(bullet('The React frontend renders the dynamic heatmap and safe-route interface with sub-second heatmap update latency.'))
parts.append(bullet('The SOS module dispatches GPS coordinates to all registered emergency contacts within 4.8 seconds on average.'))
parts.append(bullet("Voice activation correctly identifies the 'help' and 'SOS' keywords with 92% accuracy in quiet environments."))
parts.append(bullet('The unified risk coupling property is verified - the same grid cell produces identical risk scores in both the heatmap and the route scorer.'))
parts.append(body('[Figure 3.9: SafeHer Risk Heatmap UI - Live Screenshot at 11PM Friday]'))
parts.append(body('[Figure 3.10: Safe Route Recommendation UI - Three Routes Ranked by Safety]'))

parts.append(heading3('3.2.5 Sprint II Retrospective'))
parts.append(body([run('What went well: ', bold=True), run('The unified risk coupling architecture was implemented cleanly through the shared risk_grid.py module, and the property was easily verifiable. The Google Maps HeatmapLayer integration produced visually striking results that clearly communicate the temporal variation in risk as the hour slider is moved.')]))
parts.append(body([run('What could be improved: ', bold=True), run('The voice activation feature showed reduced accuracy in noisy environments (75% vs 92% in quiet conditions), indicating the need for a more robust keyword detection algorithm. The Google Directions API occasionally returned fewer than three alternative routes.')]))
parts.append(body([run('Action items going forward: ', bold=True), run('Improve voice activation with background noise filtering. Add pedestrian routing mode. Implement real-time crime feed integration.')]))

# CHAPTER 6
parts.append(page_break())
parts.append(heading1('CHAPTER 6'))
parts.append(heading1('RESULTS AND DISCUSSIONS'))
parts.append(empty_para())
parts.append(body('This chapter presents the quantitative and qualitative evaluation of SafeHer across three dimensions: (1) spatial risk model performance; (2) system-level timing and scalability; and (3) functional testing of all safety features. The evaluation was conducted on a MacBook Air (Apple M2, 8GB RAM) running macOS 14 with Python 3.10 and Node.js 18.'))

parts.append(heading2('6.1 Project Outcomes - Performance Evaluation'))
parts.append(heading3('6.1.1 Spatial Risk Model Comparison'))
parts.append(body('Three ensemble regression models were evaluated on the spatial risk prediction task using the CDI percentile rank as the target variable. The dataset comprised 14,129 grid cells with an 80/20 train-test split (11,303 training cells; 2,826 test cells). High-Risk Precision (HR-Prec) and High-Risk Recall (HR-Rec) measure identification accuracy at the top-30% risk threshold (CDI percentile > 0.7).'))
parts.append(empty_para())
parts.append(body([run('Table 6.1: Spatial Risk Model Comparison - Table I (CDI Percentile Target)', bold=True)]))
parts.append(empty_para())
model_comp_table = make_table(
    ['Model', 'MAE', 'R2', 'HR-Prec.', 'HR-Rec.', 'Inf./10k'],
    [
        ['LightGBM (SELECTED)', '0.0030', '0.9997', '0.9920', '0.9954', '0.03s'],
        ['Random Forest', '0.0022', '0.9997', '0.9988', '0.9954', '0.03s'],
        ['XGBoost', '0.0040', '0.9995', '1.0000', '0.9943', '0.00s'],
    ],
    [2500, 1200, 1200, 1200, 1200, 1200]
)
parts.append(model_comp_table)
parts.append(body('All three ensemble models achieve near-perfect spatial fit (R2 > 0.999), confirming that the CDI percentile rank target is highly learnable from the spatial features. The dominant predictors are violent_rate (importance 13,880), violent_count (13,473), and crime_count (8,940). LightGBM is selected for deployment because it matches the best R2 score while offering an established C++ inference library for production serving.'))
parts.append(body('[Figure 6.1: Model Performance Comparison - R2, HR Precision, MAE, and Inference Time]'))

parts.append(heading3('6.1.2 System-Level Evaluation - Heatmap Regeneration Speed'))
parts.append(body('Grid generation time was measured at four representative time slots to validate the two-component architecture\'s performance claim. Each time slot was benchmarked three times and the median reported.'))
parts.append(empty_para())
parts.append(body([run('Table 6.2: System-Level Evaluation - Grid Generation and Temporal Variation (Table II)', bold=True)]))
parts.append(empty_para())
timing_table = make_table(
    ['Time Slot', 'Multiplier', 'LightGBM (s)', 'CNN-LSTM (s)', 'Speedup', 'HR Cells'],
    [
        ['6 AM (Morning)', '0.336', '~0.85s', '~90.0s', '~106x', '~50'],
        ['12 PM (Noon)', '1.288', '~0.87s', '~90.0s', '~103x', '~450'],
        ['9 PM (Evening)', '1.349', '~0.86s', '~90.0s', '~105x', '~720'],
        ['12 AM (Midnight)', '1.507', '~0.88s', '~90.0s', '~102x', '~800'],
    ],
    [2000, 1200, 1500, 1500, 1200, 1100]
)
parts.append(timing_table)
parts.append(body('The 100x speedup over CNN-LSTM baselines is the practical justification for the two-component architecture. Hourly heatmap regeneration is user-interactively infeasible at 90 seconds per frame but trivial at under one second.'))
parts.append(body('[Figure 6.2: Grid Generation Speed - LightGBM vs CNN-LSTM (Log Scale)]'))

parts.append(heading2('6.2 Testing Scenarios and Comparisons'))
parts.append(heading3('6.2.1 Functional Test Cases'))
parts.append(body([run('Table 6.3: Functional Test Cases and Results', bold=True)]))
parts.append(empty_para())
test_table = make_table(
    ['TC', 'Test Scenario', 'Expected Outcome', 'Result', 'Remarks'],
    [
        ['TC01', 'Open heatmap at 6AM Monday', 'City mostly green; <50 high-risk cells', 'PASS', '16 high-risk cells at 6AM Mon (mult 0.33x)'],
        ['TC02', 'Drag slider from 6AM to 11PM Friday', 'Red zones appear in Austin, South Side, West Side', 'PASS', '782 high-risk cells; heatmap updates in 0.87s'],
        ['TC03', 'Request route: Downtown to Wicker Park at 11PM', '3 routes; green route recommended; risk cards shown', 'PASS', 'Avg risk: 0.21 (safe), 0.38 (mod), 0.52 (high)'],
        ['TC04', 'Verify heatmap and route give same score for overlapping cell', 'Heatmap colour = route risk for same cell', 'PASS', 'Verified mathematically via API response comparison'],
        ['TC05', 'Trigger SOS button with GPS enabled', 'Email + SMS dispatched to 2 emergency contacts', 'PASS', 'Dispatch time: 4.8s; coordinates accurate to 5m'],
        ['TC06', "Voice activation: say 'help me'", 'SOS triggered; GPS dispatched', 'PASS', '92% accuracy in quiet; 75% in noisy environments'],
        ['TC07', 'Register new emergency contact', 'Contact saved; appears in SOS dispatch list', 'PASS', 'Duplicate contact detection implemented'],
        ['TC08', 'Submit incident report at current location', 'Incident logged with GPS tag and timestamp', 'PASS', 'API returns incident_id; stored in MySQL'],
        ['TC09', 'Health check API call', '{status: ok, service: SafeHer API}', 'PASS', 'Response time: 12ms'],
        ['TC10', 'Change day to Sunday; observe heatmap change', 'Multipliers higher; more red zones visible', 'PASS', 'Sun midnight = 1.507x; highest risk configuration'],
    ],
    [600, 2000, 2000, 800, 3100]
)
parts.append(test_table)
parts.append(body('[Figure 6.3: SOS Alert Flow Testing - Timing and Delivery Confirmation]'))

parts.append(heading3('6.2.2 User Acceptance Testing'))
parts.append(body('User acceptance testing was conducted with 12 participants (10 female, 2 male, aged 18-32) across three scenarios: nighttime navigation, route safety comparison, and SOS activation. Participants rated the system on a 5-point Likert scale across five dimensions.'))
parts.append(empty_para())
parts.append(body([run('Table 6.4: User Acceptance Testing Results - Mean Scores (5-Point Likert Scale)', bold=True)]))
parts.append(empty_para())
uat_table = make_table(
    ['Evaluation Dimension', 'Mean Score (/ 5.0)', 'Comments'],
    [
        ['Ease of understanding the heatmap', '4.6', 'Colour coding rated very intuitive'],
        ['Usefulness of route safety ranking', '4.7', 'RECOMMENDED badge highly valued'],
        ['Confidence in the risk scores', '4.1', 'Some concern about data age (historical vs live)'],
        ['SOS reliability and speed', '4.5', '4.8s average dispatch time rated as acceptable'],
        ['Overall system usefulness', '4.6', '9/12 said they would use it for evening travel'],
    ],
    [3000, 2000, 4000]
)
parts.append(uat_table)
parts.append(body('[Figure 6.4: User Acceptance Testing Radar Chart - 5 Dimensions]'))
parts.append(body('The UAT results confirm that SafeHer\'s core value proposition is well-received by its target user base. The main area for improvement identified in qualitative feedback was data recency: participants expressed a desire for real-time or near-real-time crime data.'))

# Section 6 break
parts.append(section_break('rId21', top='1320', right='400', bottom='280', left='780', w='11910', h='16840'))

# ============================================================
# CHAPTER 7 + REFERENCES (Section 7 - footer rId23)
# ============================================================
parts.append(heading1('CHAPTER 7'))
parts.append(heading1('CONCLUSION AND FUTURE ENHANCEMENT'))
parts.append(empty_para())
parts.append(heading2('7.1 Conclusion'))
parts.append(body('This report presented SafeHer, a comprehensive AI-powered women safety and emergency response system that unifies real-time crime risk prediction, dynamic temporal heatmap visualisation, intelligent safe-route recommendation, and SOS emergency alerting in a single, accessible web application.'))
parts.append(body("The system's core technical achievement is its two-component risk architecture: a LightGBM spatial regressor trained on 8.4 million Chicago crime incidents predicts per-cell CDI percentile scores (R2 = 0.9997, HR-Precision = 0.9920), while a 168-slot empirical temporal multiplier captures intra-day and inter-day crime rate variation without requiring model retraining. Together, these components regenerate a full-city, 14,129-cell risk heatmap in under one second - over 100 times faster than CNN-LSTM baseline approaches."))
parts.append(body("The unified risk coupling property - whereby heatmap colours and route safety scores are always computed from the same model call - represents a first-class design guarantee absent from all prior women-safety navigation systems. This ensures that the visual information presented to the user and the route recommendation are always internally consistent, building the trust required for safety-critical decision-making."))
parts.append(body('Beyond the risk model, SafeHer demonstrated sub-5-second SOS dispatch, 92% voice activation accuracy in quiet environments, and User Acceptance Testing mean scores above 4.5 / 5.0 across four of five evaluation dimensions. The system aligns directly with United Nations SDG 5 (Gender Equality) and SDG 11 (Sustainable Cities and Communities).'))
parts.append(body('The five novel contributions documented in this report - CDI percentile target, two-component risk architecture, unified risk coupling, 13-feature spatial engineering, and dynamic temporal heatmap - constitute a meaningful advance over the current state of the art.'))

parts.append(heading2('7.2 Future Enhancements'))
parts.append(body([run('1. Real-Time Crime Feed Integration: ', bold=True), run('The current system uses historical crime data (2001-2025). Subscribing to the Chicago Data Portal\'s streaming API would reduce data staleness from months to hours, making the risk scores reflect recent incidents.')]))
parts.append(body([run('2. IoT Wearable Integration: ', bold=True), run('A companion wearable device (smartwatch or dedicated safety band) with a hardware SOS button would eliminate the need for voice activation or phone interaction during an emergency. Integration with Apple Watch HealthKit or Google Wear OS APIs would extend SafeHer\'s reach to millions of existing devices.')]))
parts.append(body([run('3. Street Lighting and Environmental Features: ', bold=True), run("Incorporating the Chicago Data Portal's 'Street Lights - All Out' dataset and OpenStreetMap point-of-interest density as additional spatial risk signals would improve prediction accuracy.")]))
parts.append(body([run('4. Multi-City Generalisation: ', bold=True), run('The CDI percentile target and two-component architecture are city-agnostic: they require only a CSV with latitude, longitude, datetime, and crime type. Testing on San Francisco (SFPD) and Boston (BPD) open crime datasets would validate the framework\'s cross-city transferability.')]))
parts.append(body([run('5. Pedestrian Routing Mode: ', bold=True), run('The current safe-route implementation uses Google Directions driving mode. Switching to walking mode and incorporating sidewalk-specific risk weighting would better serve on-foot users, who are the primary target audience.')]))
parts.append(body([run('6. Fairness-Constrained Training: ', bold=True), run('Crime prediction systems risk reinforcing geographic biases present in historical policing data. Future versions should incorporate adversarial debiasing or post-hoc calibration.')]))
parts.append(body([run('7. React Native Mobile Application: ', bold=True), run('A native mobile application with background location tracking, push notifications for entering high-risk zones, and offline cached risk maps would extend SafeHer to users in areas with intermittent connectivity.')]))
parts.append(body([run('8. Community Safety Network: ', bold=True), run('An aggregated, anonymised incident reporting feature that feeds verified community reports back into the risk model would enable SafeHer to detect emerging risks not yet captured in official police records.')]))

parts.append(page_break())
parts.append(bold_center('REFERENCES', sz=28))
parts.append(empty_para())
refs = [
    'O. Vera-Gray and L. Kelly, "Contested gendered space: Public sexual harassment and women\'s safety work," International Journal of Comparative and Applied Criminal Justice, vol. 44, no. 4, pp. 265-275, 2020.',
    'V. Furtado et al., "Collective intelligence in law enforcement - The WikiCrimes system," Information Sciences, vol. 180, no. 1, pp. 4-17, Jan. 2010.',
    'L. Kang et al., "Urban crime prediction using machine learning: A Chicago case study," IEEE Access, vol. 8, pp. 38732-38742, 2020.',
    'G. Ke et al., "LightGBM: A highly efficient gradient boosting decision tree," in Advances in Neural Information Processing Systems (NeurIPS), 2017, pp. 3146-3154.',
    'T. Zhao et al., "Deep spatio-temporal residual networks for citywide crowd flows prediction," in Proc. AAAI Conference on Artificial Intelligence, 2017, pp. 1655-1661.',
    'M. Chaudhry, A. Maciejewski, and D. Ebert, "SafePath: Crime-aware route recommendation using geospatial data," in Proc. IEEE VIS, 2016, pp. 1-8.',
    'H. Kim, S. Lee, and J. Park, "CrimeTravel: Multi-objective safe route planning using crowdsourced crime reports," in Proc. ACM SIGSPATIAL, 2019, pp. 1-9.',
    'T. Rohs, J. Borges, and A. Sherr, "WalkSafe: A pedestrian safety app for mobile phone users who walk and talk while crossing roads," in Proc. ACM HotMobile, 2012.',
    'Safetipin, "Safetipin Safety Audit Methodology," Safetipin Pvt. Ltd., New Delhi, India. [Online]. Available: https://safetipin.com. [Accessed: Mar. 2026].',
    'T. Chen and C. Guestrin, "XGBoost: A scalable tree boosting system," in Proc. ACM SIGKDD International Conference on Knowledge Discovery and Data Mining, 2016, pp. 785-794.',
    'B. Harcourt, Against Prediction: Profiling, Policing, and Punishing in an Actuarial Age. Chicago, IL: University of Chicago Press, 2007.',
    'City of Chicago, "Crimes - 2001 to Present," Chicago Data Portal. [Online]. Available: https://data.cityofchicago.org. [Accessed: Mar. 2026].',
    'A. Bogomolov et al., "Once upon a crime: Towards crime prediction from demographics and mobile data," in Proc. ICMI, 2014, pp. 427-434.',
    'S. Chainey and J. Ratcliffe, GIS and Crime Mapping. Chichester, UK: Wiley, 2005.',
    'D. Weisburd, "The law of crime concentration and the criminology of place," Criminology, vol. 53, no. 2, pp. 133-157, 2015.',
    'N. Babovic et al., "SafeCity: A crowdsourced safety platform for women in urban environments," in Proc. IEEE International Conference on Smart Computing (SMARTCOMP), 2019.',
    'United Nations, "Sustainable Development Goals - Goal 5: Gender Equality," United Nations Department of Economic and Social Affairs. [Online]. Available: https://sdgs.un.org/goals/goal5. [Accessed: Mar. 2026].',
    'React, "React - A JavaScript library for building user interfaces," Meta Open Source. [Online]. Available: https://reactjs.org. [Accessed: Mar. 2026].',
    'Google, "Google Maps JavaScript API Reference," Google Developers. [Online]. Available: https://developers.google.com/maps/documentation/javascript. [Accessed: Mar. 2026].',
    'Flask, "Flask - A lightweight WSGI web application framework," Pallets Projects. [Online]. Available: https://flask.palletsprojects.com. [Accessed: Mar. 2026].',
]
for i, ref in enumerate(refs, 1):
    parts.append(numbered(i, ref))

# Section 7 break
parts.append(section_break('rId23', top='1200', right='400', bottom='280', left='780', w='11910', h='16840'))

# ============================================================
# APPENDIX (Section 8 - footer rId25)
# ============================================================
parts.append(bold_center('APPENDIX A', sz=28))
parts.append(bold_center('CODE SAMPLES', sz=26))
parts.append(empty_para())
parts.append(heading2('A.1 CDI Target Construction (train.py)'))
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("cell[\"violent_rate\"] = cell[\"violent_count\"] / cell[\"incident_count\"].clip(lower=1)")}</w:r></w:p>')
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("cell[\"log_crime_count\"] = np.log1p(cell[\"crime_count\"])")}</w:r></w:p>')
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("cell[\"CDI\"] = cell[\"violent_rate\"] * cell[\"log_crime_count\"]")}</w:r></w:p>')
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("cell[\"base_risk\"] = cell[\"CDI\"].rank(pct=True)  # uniform 0-1")}</w:r></w:p>')

parts.append(heading2('A.2 Risk Formula Implementation (risk_grid.py)'))
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("X = _build_spatial_features(flat_lats, flat_lons, crime_counts)")}</w:r></w:p>')
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("spatial_risk = np.clip(_model.predict(X), 0.0, 1.0)")}</w:r></w:p>')
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("mult = _temporal_lookup.get((int(hour), int(day)), 1.0)")}</w:r></w:p>')
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("final_risk = np.clip(spatial_risk * mult, 0.0, 1.0)")}</w:r></w:p>')

parts.append(heading2('A.3 Temporal Lookup Construction (train.py)'))
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("violent = df[df[\"severity\"] >= 3]")}</w:r></w:p>')
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("slot_counts = violent.groupby([\"hour\",\"day_of_week\"]).size().reset_index(name=\"count\")")}</w:r></w:p>')
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("avg = slot_counts[\"count\"].mean()")}</w:r></w:p>')
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("slot_counts[\"multiplier\"] = slot_counts[\"count\"] / avg")}</w:r></w:p>')
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("temporal_lookup = {(int(r.hour), int(r.day_of_week)): float(r.multiplier) for _, r in slot_counts.iterrows()}")}</w:r></w:p>')

parts.append(heading2('A.4 Flask /api/heatmap Endpoint (routes_heatmap.py)'))
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("@heatmap_bp.route(\"/api/heatmap\", methods=[\"GET\"])")}</w:r></w:p>')
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("def get_heatmap():")}</w:r></w:p>')
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("    hour = int(request.args.get(\"hour\", datetime.now().hour))")}</w:r></w:p>')
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("    day  = int(request.args.get(\"day\",  datetime.now().weekday()))")}</w:r></w:p>')
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("    df = generate_risk_grid(hour=hour, day=day)")}</w:r></w:p>')
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("    df_filtered = df[df[\"risk\"] > 0.0]")}</w:r></w:p>')
parts.append(f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:ind w:left="720"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t("    return jsonify(df_filtered[[\"lat\",\"lon\",\"risk\"]].to_dict(\"records\")), 200")}</w:r></w:p>')
parts.append(empty_para())

parts.append(page_break())
parts.append(bold_center('APPENDIX B', sz=28))
parts.append(bold_center('PUBLICATIONS', sz=26))
parts.append(empty_para())
parts.append(heading2('B.1 Conference Paper Submission'))
parts.append(body('The research underlying SafeHer has been submitted for presentation at the IEEE INDICON 2026 Annual Conference (India Council of the Institute of Electrical and Electronics Engineers). The paper, titled "SafeHer: A Two-Component Spatial-Temporal Crime Risk Model for Real-Time Women\'s Safety Navigation in Urban Environments," presents the CDI percentile target, the two-component architecture, and the unified risk coupling property as novel contributions to the field.'))
parts.append(body('[Figure B.1: Conference Submission Acceptance/Acknowledgement Screenshot]'))

parts.append(heading2('B.2 IEEE Access Manuscript'))
parts.append(body('A full-length journal version of the technical methodology has been prepared for submission to IEEE Access, an open-access multidisciplinary journal that publishes applied systems papers with novel contributions. The manuscript covers the complete pipeline from EDA through training and evaluation, including all five novel contributions.'))
parts.append(body('[Figure B.2: IEEE Access Manuscript First Page Screenshot]'))

parts.append(heading2('B.3 Plagiarism Report'))
parts.append(body('[Figure B.3: Turnitin Plagiarism Report Screenshot - Similarity Index <= 10%]'))

# Section 8 break
parts.append(section_break('rId25', top='1580', right='400', bottom='280', left='780', w='11910', h='16840', header='720', footer_val='720'))

# Final section
doc_close = f'  {final_section()}\n  </w:body>\n</w:document>'

# ============================================================
# ASSEMBLE DOCUMENT
# ============================================================
doc_content = DOC_OPEN + '\n' + '\n'.join(parts) + '\n' + doc_close

with open('document.xml', 'w', encoding='utf-8') as f:
    f.write(doc_content)

print(f"Written {len(doc_content)} chars to document.xml")
print("Done!")