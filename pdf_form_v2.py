# -*- coding: utf-8 -*-
"""PDF Punch List for Kivy V30, adapted from desktop punch_list_app_v2 PDF form.
No tkinter, pymupdf or desktop dependencies. ReportLab + Pillow only.
"""
import os, io, re, unicodedata, datetime
from xml.sax.saxutils import escape
from PIL import Image, ImageOps
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, Flowable, HRFlowable, CondPageBreak, Image as PDFImage
from reportlab.lib.utils import ImageReader

NAVY=colors.HexColor('#1F3A5F')
GREY=colors.HexColor('#EEF1F5')
LINE=colors.HexColor('#9AA5B1')


def _text(value):
    return escape(unicodedata.normalize('NFC',str(value or ''))).replace('\n','<br/>')


def _font(font_path):
    if not os.path.isfile(font_path):
        raise FileNotFoundError('Không tìm thấy font tiếng Việt: '+font_path)
    if 'PLV30' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('PLV30',font_path))
        bold_path=os.path.join(os.path.dirname(font_path),'DejaVuSans-Bold.ttf')
        if os.path.isfile(bold_path):
            pdfmetrics.registerFont(TTFont('PLV30Bold',bold_path))
            pdfmetrics.registerFontFamily('PLV30',normal='PLV30',bold='PLV30Bold',italic='PLV30',boldItalic='PLV30Bold')
        else:
            pdfmetrics.registerFontFamily('PLV30',normal='PLV30',bold='PLV30',italic='PLV30',boldItalic='PLV30')
    return 'PLV30'


class CenteredMottoRule(Flowable):
    """Line placed below the motto, centered within the actual PDF column."""
    def __init__(self, length=32*mm):
        super().__init__(); self.length=length; self.width=0; self.height=8
    def wrap(self, available_width, available_height):
        self.width=available_width
        return available_width,self.height
    def draw(self):
        c=self.canv; c.saveState();c.setStrokeColor(colors.black);c.setLineWidth(.65)
        x=(self.width-self.length)/2
        c.line(x,3,x+self.length,3);c.restoreState()


class PhotoRow(Flowable):
    """Image row; portrait and landscape preserve original orientation, no crop."""
    def __init__(self, images, cell_width, width, gap=3):
        Flowable.__init__(self)
        self.images=images
        self.cell_width=cell_width
        self.width=width
        self.gap=gap
        self.height=max(img[2] for img in images)+gap
    def wrap(self, aw, ah):
        return self.width,self.height
    def draw(self):
        for col,(reader,w,h) in enumerate(self.images):
            cx=(col+.5)*self.cell_width
            self.canv.drawImage(reader,cx-w/2,self.gap/2,width=w,height=h)


def _photos(paths, width, defect_index):
    valid=[]
    for n,path in enumerate(paths or [],1):
        if not os.path.isfile(path):
            valid.append(None)
            continue
        try:
            with Image.open(path) as source:
                if source.width*source.height>80000000:
                    raise ValueError('Ảnh quá lớn')
                if source.format=='JPEG':
                    source.draft('RGB',(1600,1600))
                img=ImageOps.exif_transpose(source)
                img.thumbnail((1600,1600),Image.Resampling.LANCZOS)
                if img.mode!='RGB':
                    if 'A' in img.getbands():
                        rgba=img.convert('RGBA'); rgb=Image.new('RGB',rgba.size,'white')
                        rgb.paste(rgba,mask=rgba.getchannel('A')); img=rgb
                    else: img=img.convert('RGB')
                out=io.BytesIO();img.save(out,'JPEG',quality=88,optimize=True);out.seek(0)
                valid.append((ImageReader(out),img.width,img.height,out))
        except Exception as exc:
            raise ValueError('Lỗi %02d, ảnh %02d (%s): %s'%(defect_index,n,os.path.basename(path),exc)) from exc
    return valid


def build_pdf(path,data,font_path):
    font=_font(font_path)
    W,H=A4
    margins={'left':15*mm,'right':15*mm,'top':14*mm,'bottom':18*mm}
    body_w=W-margins['left']-margins['right']
    body_h=H-margins['top']-margins['bottom']
    def style(name,size=9.5,align=TA_LEFT,leading=None,color=colors.black,**kw):
        return ParagraphStyle(name,fontName=font,fontSize=size,leading=leading or size*1.4,alignment=align,textColor=color,**kw)
    normal=style('normal',9.5,TA_JUSTIFY)
    small=style('small',8.3,TA_LEFT)
    cell=style('cell',9.0,TA_JUSTIFY,leading=13.5,spaceAfter=7)
    head=style('head',9.0,TA_CENTER,color=colors.white)
    title=style('title',15.5,TA_CENTER,color=colors.HexColor('#E52936'),spaceAfter=5)
    centered=style('centered',9.5,TA_CENTER)
    header=style('header',8.7,TA_CENTER)
    header_left=style('header_left',9.0,TA_CENTER)
    section=style('section',10.5,TA_LEFT,color=NAVY,spaceBefore=8,spaceAfter=5)
    def P(value,st=normal):return Paragraph(_text(value),st)
    def L(label,value,st=normal):return Paragraph('<b>'+_text(label)+'</b> '+_text(value),st)
    def footer(canvas,doc):
        canvas.saveState()
        canvas.setFont(font,7.5);canvas.setFillColor(colors.grey)
        number=datetime.date.today().strftime('%d%m%y')+'/PL/CB-GS'
        left='Thông báo tồn tại (Punch List) – Số: '+number
        if len(left)>85:left=left[:82]+'...'
        canvas.drawString(margins['left'],9*mm,left)
        canvas.drawRightString(W-margins['right'],9*mm,'Trang %d'%doc.page)
        canvas.restoreState()
    doc=BaseDocTemplate(path,pagesize=A4,title='Thông báo tồn tại cần khắc phục')
    frame=Frame(margins['left'],margins['bottom'],body_w,body_h,
                leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id='A4',frames=[frame],onPage=footer))
    story=[]
    owner=data.get('owner') or 'CHỦ ĐẦU TƯ'
    board=data.get('board') or 'BAN QUẢN LÝ DỰ ÁN'
    place=data.get('location') or '........'
    today=datetime.date.today()
    date=today.strftime('%d/%m/%Y')
    number=today.strftime('%d%m%y')+'/PL/CB-GS'
    # Số văn bản được lập tự động từ ngày xuất PDF, không lấy số cũ trong JSON.
    data=dict(data,number=number)
    left_header=[Paragraph('<b><u>'+_text(board)+'</u></b>',header_left),
                 Paragraph('Số: '+_text(number),header_left)]
    right_header=[P('CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM',header),
                  P('Độc lập – Tự do – Hạnh phúc',header),
                  CenteredMottoRule(32*mm),
                  P('%s, ngày %s'%(place,date),header)]
    t=Table([[left_header,right_header]],colWidths=[body_w*.42,body_w*.58])
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
    story.extend([t,Spacer(1,11),P('THÔNG BÁO TỒN TẠI CẦN KHẮC PHỤC',title),
                  Paragraph('<b>(PUNCH LIST)</b>',centered),Spacer(1,10),
                  L('Kính gửi:',data.get('contractor') or 'Ban điều hành thi công'),Spacer(1,7)])
    project_rows=[('Dự án',data.get('project',''),'Gói thầu',data.get('package','')),
                  ('Hạng mục',data.get('section') or data.get('package',''),'Hợp đồng số',data.get('contract','')),
                  ('Ngày kiểm tra',data.get('inspection_date') or date,'Đợt kiểm tra',data.get('inspection_round','')),
                  ('Căn cứ',data.get('basis',''),'Người kiểm tra',data.get('inspector',''))]
    info_rows=[[P(a,small),P(b,small),P(c,small),P(d,small)] for a,b,c,d in project_rows]
    info=Table(info_rows,colWidths=[body_w*.15,body_w*.35,body_w*.17,body_w*.33])
    info.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.45,LINE),('BACKGROUND',(0,0),(0,-1),GREY),('BACKGROUND',(2,0),(2,-1),GREY),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story.extend([info,Spacer(1,9),P('Qua kiểm tra hiện trường, Giám sát Ban QLDA thông báo đến Nhà thầu các tồn tại, sai sót, hạng mục chưa hoàn thiện nêu tại bảng dưới đây. Đề nghị Nhà thầu khắc phục đúng yêu cầu kỹ thuật, hoàn thành trong thời hạn quy định và có văn bản thông báo để tổ chức kiểm tra, nghiệm thu lại.'),
                  CondPageBreak(55*mm),Paragraph('<b>DANH MỤC TỒN TẠI</b>',section)])
    # V32: 40% text and 60% photographs.
    LW=body_w*.40;RW=body_w-LW
    for i,item in enumerate(data.get('items',[]),1):
        pos=str(item.get('position') or '(Chưa xác định vị trí)')
        heading=[[Paragraph('<b>MỤC %02d · %s</b>'%(i,_text(pos)),head),
                  Paragraph('<b>HÌNH ẢNH HIỆN TRƯỜNG · MỤC %02d</b>'%i,head)]]
        # One image row per PDF table row; avoids unsplittable giant cells.
        images=_photos(item.get('photos',[]),RW-14,i)
        image_rows=[]
        if not images:
            image_rows=[P('(Chưa có ảnh)',small)]
        else:
            # Two columns for multiple photos; preserve original aspect ratio.
            cols=1 if len(images)==1 else 2
            cellw=(RW-14)/cols
            for idx in range(0,len(images),cols):
                chunk=images[idx:idx+cols]
                row=[]
                for photo in chunk:
                    if photo is None:continue
                    reader,w,h,_buf=photo
                    scale=min((cellw-5)/w,(110*mm if cols==1 else 60*mm)/h)
                    row.append((reader,w*scale,h*scale))
                if row:image_rows.append(PhotoRow(row,cellw,RW-14,gap=3))
                else:image_rows.append(P('(Ảnh không tồn tại)',small))
        # Ba đoạn văn liên tiếp, căn đều và bám đỉnh ô; không phân bổ
        # nội dung xuống theo chiều cao/số lượng ảnh.
        # Văn bản rất dài được chia thành các cụm để bảng vẫn có thể qua trang.
        def split_text(value, limit=750):
            value=str(value or '').strip() or '........................'
            chunks=[]
            while len(value)>limit:
                cut=value.rfind(' ',0,limit)
                if cut<limit//3:cut=limit
                chunks.append(value[:cut].strip())
                value=value[cut:].strip()
            if value:chunks.append(value)
            return chunks
        text_paras=[]
        severity=str(item.get('severity') or 'Trung bình').strip()
        if severity not in ('Cao','Trung bình','Thấp'): severity='Trung bình'
        for key,label in [('content','Nội dung:'),('action','Yêu cầu khắc phục:'),('deadline','Thời hạn:')]:
            value=item.get(key,'')
            if key=='deadline' and not str(value or '').strip():
                value='Theo yêu cầu của Ban QLDA'
            for j,part in enumerate(split_text(value)):
                text_paras.append(L(label if j==0 else '',part,cell))
            if key=='content':
                sev_color={'Cao':'#B42318','Trung bình':'#B86E12','Thấp':'#21764B'}[severity]
                text_paras.append(Paragraph('<b>Mức độ:</b> <font color="'+sev_color+'"><b>'+severity+'</b></font>',cell))
        # Hạn chế chiều cao một ô bảng để ReportLab không báo LayoutError.
        text_groups=[]; group=[]
        for paragraph in text_paras:
            if len(group)>=7:
                text_groups.append(group);group=[]
            group.append(paragraph)
        if group:text_groups.append(group)
        count=max(len(text_groups),len(image_rows),1)
        rows=heading[:]
        for j in range(count):
            rows.append([text_groups[j] if j<len(text_groups) else '',
                         [image_rows[j]] if j<len(image_rows) else ''])
        table=Table(rows,colWidths=[LW,RW],repeatRows=1,splitByRow=1,hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),
            ('BOX',(0,0),(-1,-1),.55,LINE),('LINEBEFORE',(1,0),(1,-1),.5,LINE),
            ('LINEBELOW',(0,0),(-1,0),.5,LINE),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('TOPPADDING',(0,0),(-1,0),6),('BOTTOMPADDING',(0,0),(-1,0),6),
            ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
            ('TOPPADDING',(0,1),(-1,-1),4),('BOTTOMPADDING',(0,1),(-1,-1),4)]))
        story.extend([table,Spacer(1,7)])
    # Dòng mức độ giữ đúng nguyên văn đã được người dùng phê duyệt,
    # không thêm đầu đề chú thích hoặc diễn giải.
    story.extend([
        P('Mức độ: Cao – ảnh hưởng chất lượng, kết cấu, an toàn; '
          'Trung bình – ảnh hưởng thẩm mỹ, công năng; '
          'Thấp – hoàn thiện, vệ sinh.',small),
        Spacer(1,5),
    ])
    story.extend([Paragraph('<b>YÊU CẦU ĐỐI VỚI NHÀ THẦU</b>',section),
        P('1. Khắc phục toàn bộ tồn tại nêu trên trong thời hạn quy định; hạng mục mức độ Cao phải có biện pháp xử lý được chấp thuận trước khi thi công.'),
        P('2. Ghi nhận hình ảnh trước – trong – sau khi khắc phục, lập hồ sơ nghiệm thu bổ sung (nếu có).'),
        P('3. Có văn bản thông báo hoàn thành để bộ phận giám sát Ban QLDA kiểm tra lại; việc chậm khắc phục có thể ảnh hưởng đến nghiệm thu, thanh toán theo hợp đồng.'),
        P('4. Chi phí khắc phục tồn tại do lỗi của Nhà thầu do Nhà thầu chịu.'),
        Spacer(1,14)])
    # Khối kết văn bản: Nơi nhận / Đính kèm bên trái, duy nhất Chủ đầu tư / Ban QLDA bên phải.
    signature_name=str(data.get('inspector') or data.get('signature_name') or '').strip()
    signature_date=str(data.get('signature_date') or date).strip()
    sig_path=str(data.get('signature_path') or '').strip()
    if not sig_path:
        demo=os.path.join(os.path.dirname(__file__),'ChuKy_MAU.png')
        if os.path.isfile(demo):sig_path=demo
    sig_mark=Spacer(1,23*mm)
    if sig_path and os.path.isfile(sig_path):
        try:
            with Image.open(sig_path) as raw:
                pic=ImageOps.exif_transpose(raw).convert('RGBA')
                pic.thumbnail((700,400),Image.Resampling.LANCZOS)
                buf=io.BytesIO();pic.save(buf,'PNG');buf.seek(0)
                w,h=pic.size;scale=min(47*mm/w,22*mm/h)
                sig_mark=PDFImage(buf,width=w*scale,height=h*scale,mask='auto')
        except Exception as exc:
            raise ValueError('Không đọc được ảnh chữ ký: '+str(exc)) from exc
    sig_head=Paragraph('<b>CHỦ ĐẦU TƯ / BAN QLDA</b>',centered)
    sig_note=Paragraph('<i>(Ký và ghi rõ họ và tên)</i>',centered)
    sig_foot=[]
    if signature_name:sig_foot.append(Paragraph('<b>'+_text(signature_name)+'</b>',centered))
    sig_foot.append(P('Ngày: '+signature_date,centered))
    left_notes=[Paragraph('<b><i>Nơi nhận:</i></b>',small),P('- Như trên;',small),
                P('- Lưu hồ sơ dự án.',small),Spacer(1,5),
                Paragraph('<b><i>Đính kèm:</i></b>',small),
                P(data.get('attachment_note') or 'Không',small)]
    # A centered image cell prevents the signature from shifting to the left.
    sig_image=Table([[sig_mark]],colWidths=[body_w*.45-10],hAlign='CENTER')
    sig_image.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),0),
        ('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),4),
        ('BOTTOMPADDING',(0,0),(-1,-1),2)]))
    final=Table([[left_notes,[sig_head,sig_note,sig_image,*sig_foot]]],
                colWidths=[body_w*.55,body_w*.45],hAlign='LEFT')
    final.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
             ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4)]))
    story.append(final)
    doc.build(story)
