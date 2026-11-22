# -*- coding: utf-8 -*-
"""Thông báo lỗi thi công - Android (Kivy). Mỗi thẻ chat = một lỗi."""
import os, json, uuid, shutil, datetime, traceback, threading, copy
from xml.sax.saxutils import escape
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.popup import Popup
from kivy.uix.image import Image, AsyncImage
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.filechooser import FileChooserListView, FileChooserIconView
from kivy.graphics import Color, RoundedRectangle, Line, Triangle, StencilPush, StencilUse, StencilUnUse, StencilPop
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.widget import Widget
from kivy.uix.modalview import ModalView
from kivy.uix.floatlayout import FloatLayout
from kivy.utils import platform
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image as RLImage, LongTable
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage, ImageOps

BASE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(BASE, 'DejaVuSans.ttf')
if not os.path.isfile(FONT):
    FONT = 'Roboto'

# Pydroid 3 / Kivy 2.3.x + Android IME: Gboard/Samsung autocomplete can
# resend composing text, resulting in duplicated or wrongly placed characters.
# The documented 'null' mode generates key events without Android IME
# suggestions/composition. Leave this as 'null' for the anti-duplication fix.
# If a particular Vietnamese keyboard does not support accents in this mode,
# change to 'text' and disable keyboard predictions directly in the keyboard.
ANDROID_INPUT_MODE = 'null' if platform == 'android' else 'text'

# Unicode font family with actual bold glyphs for chat field captions.
RICH_FONT = FONT
_bold_path = os.path.join(BASE, 'DejaVuSans-Bold.ttf')
if os.path.isfile(FONT) and os.path.isfile(_bold_path):
    try:
        LabelBase.register(name='PunchListV37', fn_regular=FONT, fn_bold=_bold_path)
        RICH_FONT = 'PunchListV37'
    except Exception:
        RICH_FONT = FONT


def _kivy_safe(text):
    """Do not interpret brackets inside a user's defect as Kivy markup."""
    return str(text or '').replace('[', '&bl;').replace(']', '&br;')


def btn(text, callback, bg=(0.11, .42, .75, 1), height=44):
    b = Button(text=text, size_hint_y=None, height=dp(height), background_normal='', background_color=bg,
               font_name=FONT, font_size='13sp')
    b.bind(on_release=callback)
    return b



class VectorIconButton(ButtonBehavior, Widget):
    """Vector icons independent of Android font glyph support."""
    def __init__(self, icon='plus', ink=(.29,.37,.42,1), **kwargs):
        super().__init__(**kwargs)
        self.icon=icon
        self.ink=ink
        self.bind(pos=self._paint,size=self._paint)
        Clock.schedule_once(lambda dt:self._paint(),0)

    def _paint(self,*_):
        self.canvas.clear()
        cx=self.center_x; cy=self.center_y
        # Keep the drawing visually small while retaining a comfortable touch target.
        r=dp(6.0 if self.icon in ('plus','send','edit','up','down') else 5.5)
        with self.canvas:
            Color(*self.ink)
            if self.icon=='plus':
                Line(points=[cx-r,cy,cx+r,cy],width=dp(1.7),cap='round')
                Line(points=[cx,cy-r,cx,cy+r],width=dp(1.7),cap='round')
            elif self.icon=='send':
                Triangle(points=[cx-r,cy-r*.85,cx+r,cy,cx-r,cy+r*.85])
                Color(1,1,1,1)
                Line(points=[cx-r*.8,cy,cx+r*.15,cy],width=dp(1.4))
            elif self.icon=='close':
                Line(points=[cx-r,cy-r,cx+r,cy+r],width=dp(1.5),cap='round')
                Line(points=[cx-r,cy+r,cx+r,cy-r],width=dp(1.5),cap='round')
            elif self.icon=='up':
                Line(points=[cx,cy-r,cx,cy+r],width=dp(1.7),cap='round')
                Line(points=[cx-r*.6,cy+r*.35,cx,cy+r,cx+r*.6,cy+r*.35],width=dp(1.7),cap='round')
            elif self.icon=='down':
                Line(points=[cx,cy+r,cx,cy-r],width=dp(1.7),cap='round')
                Line(points=[cx-r*.6,cy-r*.35,cx,cy-r,cx+r*.6,cy-r*.35],width=dp(1.7),cap='round')
            elif self.icon=='edit':
                Line(points=[cx-r*.72,cy-r*.55,cx+r*.43,cy+r*.6],width=dp(2.2),cap='round')
                Line(points=[cx-r*.98,cy-r*.95,cx-r*.72,cy-r*.55],width=dp(1.5))
                Line(points=[cx+r*.43,cy+r*.6,cx+r*.68,cy+r*.35],width=dp(1.6))
                Line(points=[cx-r,cy-r,cx-r*.35,cy-r],width=dp(1.2))


def icon_btn(symbol, callback, width=34, height=34, color=(.35,.43,.47,1), font_size=18):
    mapping={'＋':'plus','➤':'send','×':'close','✎':'edit','↑':'up','↓':'down'}
    widget=VectorIconButton(icon=mapping.get(symbol,'plus'),ink=color,
                            size_hint=(None,None),size=(dp(width),dp(height)))
    widget.bind(on_release=callback)
    return widget


def lbl(text, size=13, bold=False, height=30):
    return Label(text=text, font_name=FONT, font_size=f'{size}sp', bold=bold,
                 color=(.12, .17, .23, 1), size_hint_y=None, height=dp(height), halign='left', valign='middle')


def field(value='', hint='', multiline=False):
    """TextInput native Kivy: background opaque so touch/cursor work on Android."""
    inp = TextInput(text=str(value or ''), hint_text=hint, multiline=multiline,
                    font_name=FONT, font_size='14sp',
                    size_hint_y=None, height=dp(88 if multiline else 49),
                    background_normal='', background_active='',
                    background_color=(.96, .98, 1, 1),
                    foreground_color=(.08, .17, .23, 1),
                    cursor_color=(.05, .42, .72, 1),
                    selection_color=(.28, .62, .85, .35),
                    readonly=False, disabled=False,
                    keyboard_suggestions=False, input_type=ANDROID_INPUT_MODE,
                    padding=[dp(10), dp(10), dp(10), dp(8)])
    return inp


class PhotoTap(ButtonBehavior, Image):
    """Chạm ngắn: xem ảnh. Nhấn giữ: chỉ mở hộp thoại gỡ ảnh.

    Không bind on_release trực tiếp ở nơi sử dụng: Kivy dispatch on_release
    tới các callback đã bind ngay cả khi on_release() của lớp trả về sớm.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tap_callback = None
        self.long_press_callback = None
        self._hold_event = None
        self._hold_touch = None
        self._hold_triggered = False
        self._hold_start = None
        # Bo góc ảnh nhẹ bằng stencil, không thay đổi ảnh gốc hay hành vi chạm.
        # Dùng 5dp để ảnh trong lưới 2 cột vẫn sát nhau như Zalo.
        with self.canvas.before:
            StencilPush()
            self._rounded_clip_start = RoundedRectangle(pos=self.pos, size=self.size,
                                                        radius=[dp(5)])
            StencilUse()
        with self.canvas.after:
            StencilUnUse()
            self._rounded_clip_end = RoundedRectangle(pos=self.pos, size=self.size,
                                                      radius=[dp(5)])
            StencilPop()
        self.bind(pos=self._update_rounded_clip, size=self._update_rounded_clip)

    def _update_rounded_clip(self, *_):
        self._rounded_clip_start.pos = self.pos
        self._rounded_clip_start.size = self.size
        self._rounded_clip_end.pos = self.pos
        self._rounded_clip_end.size = self.size

    def on_touch_down(self, touch):
        inside = self.collide_point(*touch.pos)
        accepted = super().on_touch_down(touch)
        if inside and self.long_press_callback and accepted:
            self._hold_touch = touch
            self._hold_start = touch.pos
            self._hold_triggered = False
            self._hold_event = Clock.schedule_once(self._on_hold, .65)
        return accepted

    def on_touch_move(self, touch):
        if touch is self._hold_touch:
            x0, y0 = self._hold_start or touch.pos
            if (not self.collide_point(*touch.pos) or
                    abs(touch.x-x0) > dp(12) or abs(touch.y-y0) > dp(12)):
                self._cancel_hold()
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch is self._hold_touch:
            self._cancel_hold()
        return super().on_touch_up(touch)

    def _cancel_hold(self):
        if self._hold_event is not None:
            self._hold_event.cancel()
            self._hold_event = None
        self._hold_touch = None
        self._hold_start = None

    def _on_hold(self, dt):
        self._hold_event = None
        if self._hold_touch is not None and self.long_press_callback:
            self._hold_triggered = True
            self.long_press_callback()

    def on_release(self):
        if self._hold_triggered:
            self._hold_triggered = False
            return
        if self.tap_callback:
            self.tap_callback()

class DefectApp(App):
    title = 'Punch List V38 - Bãi Xép'
    def build(self):
        self.root_dir=os.path.join(self.user_data_dir,'PunchList')
        os.makedirs(self.root_dir,exist_ok=True)
        self.images_dir=os.path.join(self.root_dir,'images')
        os.makedirs(self.images_dir,exist_ok=True)
        self.db=os.path.join(self.root_dir,'hoso.json')
        self.settings_path=os.path.join(self.root_dir,'cai_dat.json')
        self.settings=self.load_settings()
        self.visible_limit=8
        self._thumb_pending=set()
        self._thumb_lock=threading.Lock()
        self._pdf_busy=False
        self._pdf_page_token=0
        self.thumb_dir=os.path.join(self.root_dir,'thumbnails')
        os.makedirs(self.thumb_dir,exist_ok=True)
        self.data={'owner':'CÔNG TY CP XD TM DL SAO VIỆT','board':'BAN QLDA BÃI XÉP',
          'project':'Khu du lịch biển Bãi Xép','contractor':'','package':'',
          'number':'','location':'','deadline':'','items':[],
          'section':'','contract':'','inspection_date':'','inspection_round':'',
          'basis':'','inspector':'','signature_name':'','signature_date':'',
          'signature_path':'','attachment_note':'Không'}
        self.load()
        # below_target: Kivy dich khung nhap dang focus len tren ban phim Android.
        # Khac resize: hoat dong ngay ca khi Pydroid 3 khong cap nhat chieu cao Window.
        Window.softinput_mode = 'below_target' if platform == 'android' else 'resize'
        root=BoxLayout(orientation='vertical',spacing=0)
        with root.canvas.before:
            Color(.785,.835,.885,1)  # Nen phan cach dam hon, giu vien the loi mong
            root_bg=RoundedRectangle(pos=root.pos,size=root.size,radius=[0])
        root.bind(pos=lambda w,v:setattr(root_bg,'pos',v),size=lambda w,v:setattr(root_bg,'size',v))
        # Thanh chức năng như ứng dụng chat: trắng, có đường phân cách và nút phẳng.
        bar=BoxLayout(size_hint_y=None,height=dp(52),spacing=dp(7),
                      padding=[dp(12),dp(7),dp(12),dp(7)])
        with bar.canvas.before:
            Color(1,1,1,1)
            bar_bg=RoundedRectangle(pos=bar.pos,size=bar.size,radius=[0])
            Color(.85,.88,.91,1)
            bar_line=Line(points=[],width=dp(.8))
        def sync_bar(w,*_):
            bar_bg.pos=w.pos;bar_bg.size=w.size
            bar_line.points=[w.x,w.y,w.right,w.y]
        bar.bind(pos=sync_bar,size=sync_bar)
        # Hai icon gon: ho so va xem PDF. Khong con nut Luu PDF tren thanh tren.
        bar.add_widget(icon_btn('✎',lambda *_:self.header(),width=43,height=38,
                                color=(.16,.38,.57,1)))
        bar.add_widget(icon_btn('➤',lambda *_:self.show_pdf(),width=43,height=38,
                                color=(.10,.48,.62,1)))
        bar.add_widget(Widget())
        bar.add_widget(Label(text='PUNCH LIST',font_name=FONT,font_size='12sp',
                             color=(.26,.38,.49,1),size_hint_x=None,width=dp(110)))
        root.add_widget(bar)
        self.scroll=ScrollView(do_scroll_x=False,bar_width=dp(3), scroll_type=['content'], scroll_distance=dp(12), scroll_timeout=180)
        self.cards=GridLayout(cols=1,size_hint_y=None,spacing=dp(17),padding=[dp(10),dp(15),dp(10),dp(18)])
        self.cards.bind(minimum_height=self.cards.setter('height'))
        self.scroll.add_widget(self.cards)
        root.add_widget(self.scroll)
        # Khung soạn thảo duy nhất, nút ảnh và gửi nằm cùng hàng như Zalo.
        composer=BoxLayout(orientation='vertical',size_hint_y=None,height=dp(81),
                           padding=[dp(10),dp(5),dp(10),dp(7)],spacing=dp(3))
        with composer.canvas.before:
            Color(1,1,1,1)
            composer_bg=RoundedRectangle(pos=composer.pos,size=composer.size,radius=[0])
            Color(.85,.88,.91,1)
            composer_line=Line(points=[],width=dp(.8))
        def sync_composer(w,*_):
            composer_bg.pos=w.pos;composer_bg.size=w.size
            composer_line.points=[w.x,w.top,w.right,w.top]
        composer.bind(pos=sync_composer,size=sync_composer)
        self.composer_bar=composer
        self.pending=[]
        self.pending_info=Label(text='',font_name=FONT,font_size='11sp',
                                color=(.12,.48,.36,1),size_hint_y=None,height=dp(17),
                                halign='left',valign='middle')
        self.pending_info.bind(size=lambda w,v:setattr(w,'text_size',(v[0],None)))
        composer.add_widget(self.pending_info)
        entry=BoxLayout(size_hint_y=None,height=dp(52),spacing=dp(3),padding=[dp(5),0,dp(5),0])
        with entry.canvas.before:
            Color(.963,.970,.979,1)
            entry_bg=RoundedRectangle(pos=entry.pos,size=entry.size,radius=[dp(14)])
            Color(.85,.88,.91,1)
            entry_border=Line(rounded_rectangle=(entry.x,entry.y,entry.width,entry.height,dp(14)),width=dp(.8))
        def sync_entry(w,*_):
            entry_bg.pos=w.pos;entry_bg.size=w.size
            entry_border.rounded_rectangle=(w.x,w.y,w.width,w.height,dp(14))
        entry.bind(pos=sync_entry,size=sync_entry)
        entry.add_widget(icon_btn('＋',lambda *_:self.attach_to_latest(),
                                  width=29,height=52,color=(.38,.43,.47,1),font_size=18))
        self.compose=TextInput(hint_text='Nhập lỗi thi công...',multiline=True,
             keyboard_suggestions=False,input_type=ANDROID_INPUT_MODE,
             font_name=FONT,font_size='14sp',size_hint_y=None,height=dp(52),
             background_normal='',background_active='',background_color=(0,0,0,0),
             foreground_color=(.10,.18,.23,1),cursor_color=(.08,.44,.78,1),
             padding=[dp(6),dp(12),dp(4),dp(6)])
        entry.add_widget(self.compose)
        send=icon_btn('➤',lambda *_:self.quick_send(),width=30,height=52,color=(.08,.52,.42,1),font_size=18)
        entry.add_widget(send)
        # Cố định chiều rộng nút; ô nhập chiếm toàn bộ phần còn lại.
        # Hai biểu tượng có kích thước riêng; ô nhập chiếm hết chiều ngang còn lại.
        composer.add_widget(entry)
        self.compose.bind(focus=self._composer_focus)
        self.compose.bind(text=self._composer_text_changed)
        root.add_widget(composer)
        self.render()
        return root

    def on_pause(self):
        # Keep the app alive while Android's image/document picker is open.
        return True

    def on_resume(self):
        pass

    def _composer_focus(self, widget, focused):
        # Giu khung nhap o day layout; below_target se nang no len tren ban phim.
        # Khong ep scroll_y khi ban phim dang mo (de tranh giat giao dien).
        if focused:
            Clock.schedule_once(lambda dt: self._ensure_composer_visible(), .12)

    def _composer_text_changed(self, widget, value):
        # De text input tu cuon con tro, khong thay doi toa do khung chat.
        pass

    def _ensure_composer_visible(self):
        if self.compose.focus:
            pass  # Khong ghi lai cursor trong khi IME dang ghep ky tu


    def load_settings(self):
        try:
            with open(self.settings_path,encoding='utf-8') as f:
                value=json.load(f)
            return value if isinstance(value,dict) else {}
        except (OSError,ValueError):return {}

    def remember(self,key,value):
        self.settings[key]=value
        try:
            tmp=self.settings_path+'.tmp'
            with open(tmp,'w',encoding='utf-8') as f:
                json.dump(self.settings,f,ensure_ascii=False,indent=2)
            os.replace(tmp,self.settings_path)
        except OSError:pass

    def thumbnail_path(self,photo):
        """EXIF xoay dung chieu ngay lan dau; cache theo mtime va kich thuoc.
        Khong tra lai anh goc khi cache chua san sang (Kivy de xoay sai EXIF).
        """
        import hashlib
        try:
            st=os.stat(photo)
            signature='%s:%s:%s:v30'%(photo,st.st_mtime_ns,st.st_size)
            key=hashlib.sha1(signature.encode('utf-8')).hexdigest()
            dest=os.path.join(self.thumb_dir,key+'.jpg')
            if not os.path.isfile(dest):
                with PILImage.open(photo) as raw:
                    im=ImageOps.exif_transpose(raw).convert('RGB')
                    im.thumbnail((720,720),PILImage.Resampling.LANCZOS)
                    tmp=dest+'.tmp'
                    im.save(tmp,format='JPEG',quality=83)
                    os.replace(tmp,dest)
            return dest
        except Exception:
            return photo

    def request_thumbnail(self, path, widget):
        """Only cached image decoding is performed on the UI thread.
        PIL EXIF normalization runs on a background thread and is shared by tiles.
        """
        import hashlib
        try:
            st=os.stat(path)
            key=hashlib.sha1(('%s:%s:%s:v30'%(path,st.st_mtime_ns,st.st_size)).encode('utf-8')).hexdigest()
            dest=os.path.join(self.thumb_dir,key+'.jpg')
        except OSError:
            return
        if os.path.isfile(dest):
            widget.source=dest
            return
        # A placeholder avoids loading the full-resolution original.
        widget.source=''
        with self._thumb_lock:
            if path in self._thumb_pending:
                def wait_cache(dt):
                    if widget.parent is None:
                        return False
                    if os.path.isfile(dest):
                        widget.source=dest
                        return False
                    return True
                Clock.schedule_interval(wait_cache,.25)
                return
            self._thumb_pending.add(path)
        def worker():
            try:
                self.thumbnail_path(path)
            finally:
                with self._thumb_lock:
                    self._thumb_pending.discard(path)
                def refresh(dt):
                    # Widgets may have been removed by a subsequent render.
                    if os.path.isfile(dest) and widget.parent is not None:
                        widget.source=dest
                Clock.schedule_once(refresh,0)
        threading.Thread(target=worker,daemon=True).start()

    def show_pdf(self):
        if not getattr(self,'last_pdf',None) or not os.path.isfile(self.last_pdf[0]):
            self.export_pdf()
        else:
            self.preview_pdf()

    def notify(self,message):
        wrap=BoxLayout(orientation='vertical',padding=dp(12),spacing=dp(8))
        message_label=Label(text=str(message),font_name=FONT,font_size='12sp',halign='center',valign='middle')
        message_label.bind(size=lambda w,v:setattr(w,'text_size',(v[0]-dp(10),None)))
        wrap.add_widget(message_label)
        pop=Popup(title='Thông báo',content=wrap,size_hint=(.93,None),height=dp(230))
        wrap.add_widget(btn('Đóng',lambda *_:pop.dismiss(),height=42))
        pop.open()

    def save(self):
        self.last_pdf=None
        tmp=self.db+'.tmp'
        with open(tmp,'w',encoding='utf-8') as f:json.dump(self.data,f,ensure_ascii=False,indent=2)
        os.replace(tmp,self.db)

    def load(self):
        try:
            with open(self.db,encoding='utf-8') as f:d=json.load(f)
            if isinstance(d,dict) and isinstance(d.get('items'),list):self.data.update(d)
        except (OSError,ValueError):pass

    def bubble_label(self,text,size=13,color=(.1,.2,.25,1)):
        l=Label(text=str(text),font_name=FONT,font_size=f'{size}sp',color=color,
            halign='left',valign='top',size_hint_y=None)
        l.bind(width=lambda w,v:setattr(w,'text_size',(max(dp(80),v-dp(12)),None)))
        l.bind(texture_size=lambda w,v:setattr(w,'height',max(dp(25),v[1]+dp(8))))
        return l

    def detail_label(self, title, value, size=12.5):
        """Saturated blue bold caption; compact block with dynamic height.

        The body remains slate. No changes to source text or PDF formatting.
        """
        shown=str(value or '').strip() or '—'
        lab=Label(font_name=RICH_FONT,markup=True,font_size=f'{size}sp',
                  color=(.12,.18,.23,1),halign='left',valign='top',
                  size_hint_y=None,height=dp(22))
        lab.text=('[color=#0875B8][b]%s[/b][/color] %s'
                  % (_kivy_safe(title),_kivy_safe(shown)))
        lab.bind(width=lambda w,v:setattr(w,'text_size',(max(dp(80),v-dp(6)),None)))
        lab.bind(texture_size=lambda w,v:setattr(w,'height',max(dp(22),v[1]+dp(2))))
        return lab

    def render(self):
        self.cards.clear_widgets()
        if not self.data['items']:
            self.cards.add_widget(self.bubble_label('Chưa có lỗi. Nhập nội dung vào khung chat bên dưới.'))
        items=self.data['items']
        if len(items)>self.visible_limit:
            older=len(items)-self.visible_limit
            more=btn('Xem thêm %d lỗi cũ'%older,lambda *_:self.load_older(),(.35,.46,.56,1),42)
            self.cards.add_widget(more)
        for i in range(max(0,len(items)-self.visible_limit),len(items)):
            item=items[i]
            bubble=BoxLayout(orientation='vertical',size_hint_y=None,spacing=dp(7),padding=[dp(13),dp(10),dp(13),dp(10)])
            bubble.bind(minimum_height=bubble.setter('height'))
            with bubble.canvas.before:
                Color(1,1,1,1)
                rect=RoundedRectangle(pos=bubble.pos,size=bubble.size,radius=[dp(12)])
                Color(.82,.85,.88,1)
                outline=Line(rounded_rectangle=(bubble.x,bubble.y,bubble.width,bubble.height,dp(12)),width=dp(.7))
            def sync_bubble(w,*_,r=rect,line=outline):
                r.pos=w.pos;r.size=w.size
                line.rounded_rectangle=(w.x,w.y,w.width,w.height,dp(12))
            bubble.bind(pos=sync_bubble,size=sync_bubble)
            # Thanh tiêu đề: dấu × nhỏ ở góc trên phải, không chiếm hàng thao tác.
            heading=BoxLayout(size_hint_y=None,height=dp(30),spacing=dp(2))
            title=self.bubble_label('LỖI %02d  ·  %s'%(i+1,item.get('position','')),12,color=(.12,.40,.65,1))
            heading.add_widget(title)
            heading.add_widget(icon_btn('×',lambda _,j=i:self.delete(j),
                                        width=31,height=29,color=(.53,.57,.60,1),font_size=17))
            bubble.add_widget(heading)
            separator=Widget(size_hint_y=None,height=dp(1))
            with separator.canvas:
                Color(.79,.84,.88,1)
                separator_rule=Line(points=[],width=dp(.7))
            separator.bind(pos=lambda w,v,l=separator_rule:setattr(l,'points',[w.x,w.center_y,w.right,w.center_y]),
                           size=lambda w,v,l=separator_rule:setattr(l,'points',[w.x,w.center_y,w.right,w.center_y]))
            bubble.add_widget(separator)
            # All four canonical PDF fields are visible immediately ABOVE photos.
            # Captions are navy/bold in Kivy; the PDF has black/bold captions.
            level=item.get('severity') or 'Trung bình'
            if level not in ('Cao','Trung bình','Thấp'):
                level='Trung bình'
            # Bốn đoạn sát nhau trong một nhóm riêng, tránh khoảng cách
            # 7dp của thẻ lỗi giữa mỗi đoạn trong khi vẫn giữ chữ xuống dòng.
            details=BoxLayout(orientation='vertical',size_hint_y=None,spacing=dp(2))
            details.bind(minimum_height=details.setter('height'))
            details.add_widget(self.detail_label('Nội dung:',item.get('content',''),13))
            details.add_widget(self.detail_label('Mức độ:',level,12.5))
            details.add_widget(self.detail_label('Yêu cầu khắc phục:',item.get('action',''),12.5))
            details.add_widget(self.detail_label('Thời hạn:',item.get('deadline',''),12.5))
            bubble.add_widget(details)
            photos=[x for x in item.get('photos',[]) if os.path.isfile(x)]
            if photos:
                # Bố cục theo số ảnh như Zalo: 1 ảnh lớn, 2 ảnh ngang hàng,
                # 3 ảnh: 1 lớn + 2 nhỏ, 4 ảnh: lưới 2x2,
                # 5+ ảnh: 1 lớn + lưới 2 cột. Không giấu ảnh.
                # Ảnh giữ tỷ lệ gốc khi xem toàn màn hình; ô lưới dùng cover.
                gallery=BoxLayout(orientation='vertical',size_hint_y=None,spacing=dp(2))
                gallery.bind(minimum_height=gallery.setter('height'))
                def photo_tile(path, index, height):
                    tile=PhotoTap(source='',
                                  size_hint_y=None,height=dp(height),fit_mode='cover')
                    self.request_thumbnail(path,tile)
                    tile.tap_callback=lambda paths=list(photos),n=index:self.preview_photos(paths,n)
                    tile.long_press_callback=lambda uid=item.get('id'),p=path:self.confirm_chat_photo_remove(uid,p)
                    return tile
                def photo_grid(entries, height=190):
                    grid=GridLayout(cols=2,size_hint_y=None,spacing=dp(2),
                                    row_default_height=dp(height),row_force_default=True)
                    grid.bind(minimum_height=grid.setter('height'))
                    for index,path in entries:
                        grid.add_widget(photo_tile(path,index,height))
                    if len(entries)%2:
                        grid.add_widget(Widget())
                    return grid
                nphotos=len(photos)
                if nphotos == 1:
                    # Ảnh đơn: khung lớn nhưng không kéo giãn méo ảnh.
                    gallery.add_widget(photo_tile(photos[0],0,290))
                elif nphotos in (2,4):
                    gallery.add_widget(photo_grid(list(enumerate(photos)),210))
                else:
                    gallery.add_widget(photo_tile(photos[0],0,290))
                    gallery.add_widget(photo_grid(list(enumerate(photos[1:],start=1)),190))
                bubble.add_widget(gallery)
            # Cụm thao tác nhỏ, chỉ biểu tượng, căn trái.
            buttons=BoxLayout(size_hint_y=None,height=dp(34),spacing=dp(5))
            buttons.add_widget(icon_btn('✎',lambda _,j=i:self.edit_item(j),
                                        width=35,height=34,font_size=15))
            buttons.add_widget(icon_btn('↑',lambda _,j=i:self.move(j,-1),
                                        width=35,height=34,font_size=15))
            buttons.add_widget(icon_btn('↓',lambda _,j=i:self.move(j,1),
                                        width=35,height=34,font_size=15))
            buttons.add_widget(Widget())
            bubble.add_widget(buttons)
            self.cards.add_widget(bubble)
        Clock.schedule_once(lambda dt:setattr(self.scroll,'scroll_y',0),.12)

    def load_older(self):
        self.visible_limit+=8
        self.render()
        Clock.schedule_once(lambda dt:setattr(self.scroll,'scroll_y',1),.1)

    def attach_to_latest(self):
        """Zalo-style: + adds images directly to the newest sent defect."""
        if not self.data['items']:
            # Preserve the previous draft workflow when no defect has been sent.
            self.pick_images(self.pending, self.update_pending)
            return
        latest=self.data['items'][-1]
        photos=latest.setdefault('photos',[])
        def attached():
            self.save()
            self.last_pdf=None
            self.render()
            self.scroll.scroll_y=0
        self.pick_images(photos,attached)

    def confirm_chat_photo_remove(self,item_id,photo_path):
        """Long press photo in a sent bubble; remove reference only after confirmation."""
        item=next((x for x in self.data['items'] if x.get('id')==item_id),None)
        if item is None or photo_path not in item.get('photos',[]):return
        content=BoxLayout(orientation='vertical',padding=dp(12),spacing=dp(8))
        content.add_widget(lbl('Gỡ ảnh này khỏi lỗi thi công?',12,height=46))
        row=BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(8))
        pop=Popup(title='Ảnh đính kèm',content=content,size_hint=(.87,None),height=dp(190))
        row.add_widget(btn('Hủy',lambda *_:pop.dismiss(),(.90,.93,.95,1),42))
        row.children[-1].color=(.18,.29,.37,1)
        def remove(*_):
            if photo_path in item.get('photos',[]):
                item['photos'].remove(photo_path)
                self.save();self.last_pdf=None
            pop.dismiss();self.render()
        row.add_widget(btn('Gỡ ảnh',remove,(.78,.28,.27,1),42))
        content.add_widget(row);pop.open()

    def update_pending(self):
        self.pending_info.text=('📷 %d ảnh đã chọn'%len(self.pending)) if self.pending else ''

    def quick_send(self):
        message=self.compose.text.strip()
        if not message:
            self.notify('Hãy nhập nội dung lỗi thi công.');return
        self.data['items'].append({'id':str(uuid.uuid4()),'position':'','content':message,
            'action':'','deadline':'','severity':'Trung bình','photos':list(self.pending)})
        self.save();self.last_pdf=None;self.compose.text='';self.pending.clear();self.update_pending();self.render()

    def pick_images(self,target,done):
        """Use Android system picker in the standalone APK (scoped storage).

        Retain the original Kivy picker on desktop/Pydroid if the Android
        activity integration is unavailable; no data/schema changes.
        """
        if platform == 'android':
            try:
                from android_files import get_file_bridge
                bridge = get_file_bridge(self)
                if bridge is not None and bridge.pick_images(target, done):
                    return
            except Exception as exc:
                print('System image picker unavailable:', exc)
        # Original V38 in-app gallery picker follows unchanged.

        import hashlib
        from kivy.graphics import Line
        from kivy.uix.stencilview import StencilView

        class PhotoTile(ButtonBehavior, BoxLayout):
            def __init__(self, path, thumbnail, callback, width, **kw):
                super().__init__(orientation='vertical',size_hint=(None,None),
                                 width=width,height=width+dp(25),padding=dp(3),spacing=dp(3),**kw)
                self.photo=path
                # Ảnh PNG đã được bo góc từ Pillow; tránh xử lý ảnh lớn trên UI.
                self.add_widget(Image(source=thumbnail,allow_stretch=True,keep_ratio=True))
                self.add_widget(Label(text=os.path.basename(path),font_name=FONT,
                                      font_size='10sp',shorten=True,size_hint_y=None,height=dp(20)))
                with self.canvas.after:
                    self.mark=Color(0,0,0,0)
                    self.line=Line(rounded_rectangle=(self.x,self.y,self.width,self.height,dp(12)),width=dp(2))
                self.bind(pos=self.redraw,size=self.redraw)
                self.bind(on_release=lambda *_:callback(self))
            def redraw(self,*_):
                self.line.rounded_rectangle=(self.x,self.y,self.width,self.height,dp(12))
            def selected(self,yes):
                self.mark.rgba=(.05,.65,.38,1) if yes else (0,0,0,0)

        outer=BoxLayout(orientation='vertical',spacing=dp(6),padding=dp(7))
        header=BoxLayout(size_hint_y=None,height=dp(42),spacing=dp(5))
        folder_name=Label(text='Thư viện ảnh',font_name=FONT,font_size='14sp',bold=True,
                          halign='left',valign='middle')
        header.add_widget(folder_name)
        header.add_widget(btn('Bộ nhớ',lambda *_:show_folders('/storage/emulated/0'),height=40))
        outer.add_widget(header)
        sc=ScrollView(do_scroll_x=False,scroll_type=['content'],scroll_distance=dp(10))
        grid=GridLayout(cols=2,size_hint_y=None,spacing=dp(9),padding=dp(4))
        grid.bind(minimum_height=grid.setter('height'))
        sc.add_widget(grid);outer.add_widget(sc)
        status=lbl('Đang mở thư mục...',11,height=28)
        status.bind(width=lambda w,v:setattr(w,'text_size',(v,None)))
        outer.add_widget(status)
        bottom=BoxLayout(size_hint_y=None,height=dp(46),spacing=dp(7))
        outer.add_widget(bottom)
        popup=Popup(title='Chọn ảnh • 2 cột',content=outer,size_hint=(.98,.95))
        selected=set()
        state={'token':0,'folder':self.settings.get('last_image_dir','/storage/emulated/0/DCIM/Camera'),'mode':'photos'}
        allowed={'.jpg','.jpeg','.png','.webp','.bmp'}
        def tile_width():
            return max(dp(110),(sc.width-dp(32))/2)
        def rounded_thumb(path):
            try:
                stat=os.stat(path)
                key=hashlib.sha1(('%s-%s-%s'%(path,stat.st_mtime_ns,stat.st_size)).encode()).hexdigest()
                dest=os.path.join(self.thumb_dir,'rounded_'+key+'.png')
                if not os.path.isfile(dest):
                    from PIL import ImageDraw
                    with PILImage.open(path) as im:
                        im=ImageOps.exif_transpose(im).convert('RGB')
                        # Ảnh vuông kiểu Zalo, bo góc nhẹ.
                        side=min(im.size)
                        x=(im.width-side)//2;y=(im.height-side)//2
                        im=im.crop((x,y,x+side,y+side)).resize((240,240))
                        mask=PILImage.new('L',(240,240),0)
                        ImageDraw.Draw(mask).rounded_rectangle((0,0,239,239),radius=20,fill=255)
                        result=im.convert('RGBA');result.putalpha(mask)
                        temp=dest+'.tmp.png';result.save(temp,format='PNG');os.replace(temp,dest)
                return dest
            except Exception:return None
        def status_selected():
            status.text='Đã chọn %d ảnh • Chạm ảnh để chọn / bỏ chọn'%len(selected)
        def toggle(tile):
            if tile.photo in selected:selected.remove(tile.photo)
            else:selected.add(tile.photo)
            tile.selected(tile.photo in selected);status_selected()
        def render_batch(batch,token,total):
            if token!=state['token'] or state['mode']!='photos':return
            for path,thumbnail in batch:
                if thumbnail:
                    tile=PhotoTile(path,thumbnail,toggle,tile_width())
                    tile.selected(path in selected)
                    grid.add_widget(tile)
            status.text='%d ảnh mới nhất • đã chọn %d'%(total,len(selected))
        def scan(folder,token):
            try:
                entries=[]
                with os.scandir(folder) as it:
                    for e in it:
                        try:
                            if e.is_file() and os.path.splitext(e.name)[1].lower() in allowed:
                                entries.append((e.stat().st_mtime,e.path))
                        except OSError:pass
                entries.sort(reverse=True)
                files=[p for _,p in entries[:50]]
                if not files:
                    Clock.schedule_once(lambda dt:setattr(status,'text','Không có ảnh ở thư mục này. Bấm Bộ nhớ để chọn thư mục khác.'),0)
                for i in range(0,len(files),4):
                    if token!=state['token']:return
                    batch=[(p,rounded_thumb(p)) for p in files[i:i+4]]
                    Clock.schedule_once(lambda dt,b=batch,t=token,n=len(files):render_batch(b,t,n),0)
            except Exception as exc:
                Clock.schedule_once(lambda dt,msg=str(exc):setattr(status,'text','Không thể đọc ảnh: '+msg[:80]),0)
        def open_photos(folder):
            if not os.path.isdir(folder):
                status.text='Không có quyền truy cập thư mục này';return
            state['token']+=1;state['mode']='photos';state['folder']=folder
            self.remember('last_image_dir',folder)
            grid.clear_widgets();selected.clear()
            folder_name.text='Ảnh: '+os.path.basename(folder)
            status.text='Đang tải tối đa 50 ảnh...'
            sc.scroll_y=1
            threading.Thread(target=scan,args=(folder,state['token']),daemon=True).start()
        def show_folders(folder):
            state['token']+=1;state['mode']='folders'
            grid.clear_widgets();sc.scroll_y=1
            folder_name.text='Thư mục: '+os.path.basename(folder)
            status.text='Chọn thư mục để xem ảnh'
            def folder_button(text,path):
                b=btn(text,lambda *_:show_folders(path),(.18,.32,.43,1),52)
                grid.add_widget(b)
            if folder!='/storage/emulated/0':
                folder_button('↑ Thư mục cha',os.path.dirname(folder.rstrip('/')))
            try:
                with os.scandir(folder) as it:
                    dirs=sorted([(e.name,e.path) for e in it if e.is_dir()],key=lambda x:x[0].lower())
                for name,path in dirs:
                    row=BoxLayout(orientation='vertical',size_hint_y=None,height=dp(84),spacing=dp(3))
                    row.add_widget(btn('📁 '+name[:18],lambda _,p=path:show_folders(p),(.18,.32,.43,1),43))
                    row.add_widget(btn('Xem ảnh',lambda _,p=path:open_photos(p),(.05,.48,.36,1),35))
                    grid.add_widget(row)
                if not dirs:status.text='Không có thư mục con; nhấn Xem ảnh ở dưới.'
            except Exception as exc:status.text='Không thể mở: '+str(exc)[:90]
            # Một nút duy nhất để chọn thư mục đang duyệt.
            bottom.clear_widgets()
            bottom.add_widget(btn('Ảnh trong thư mục này',lambda *_:open_photos(folder),(.05,.48,.36,1)))
            bottom.add_widget(btn('Hủy',lambda *_:popup.dismiss()))
        def accept(*_):
            paths=list(selected)
            if not paths:
                status.text='Chưa chọn ảnh';return
            popup.dismiss()
            def copy_files():
                copied=[]
                for path in paths:
                    try:
                        ext=os.path.splitext(path)[1].lower()
                        dest=os.path.join(self.images_dir,uuid.uuid4().hex+ext)
                        shutil.copy2(path,dest)
                        copied.append(dest)
                    except Exception:pass
                Clock.schedule_once(lambda dt:(target.extend(copied),done()),0)
            threading.Thread(target=copy_files,daemon=True).start()
        bottom.add_widget(btn('Hủy',lambda *_:popup.dismiss()))
        bottom.add_widget(btn('Thêm ảnh (0)',accept,(.05,.52,.36,1)))
        def update_count(*_):
            if state['mode']=='photos' and len(bottom.children)>0:
                # Nút cập nhật chỉ khi còn tồn tại.
                for child in bottom.children:
                    if isinstance(child,Button) and child.text.startswith('Thêm ảnh'):
                        child.text='Thêm ảnh (%d)'%len(selected)
        # Cập nhật số lượng trên nút mà không tạo widget mới.
        old_toggle=toggle
        def toggle(tile):
            old_toggle(tile);update_count()
        folder=state['folder']
        if not os.path.isdir(folder):folder='/storage/emulated/0/DCIM'
        open_photos(folder)
        popup.open()

    def preview_photos(self,photos,start=0):
        photos=[p for p in photos if os.path.isfile(p)]
        if not photos:return
        index=[min(start,len(photos)-1)]
        outer=BoxLayout(orientation='vertical')
        viewer=Image(source=self.thumbnail_path(photos[index[0]]))
        outer.add_widget(viewer)
        nav=BoxLayout(size_hint_y=None,height=dp(50),spacing=dp(4))
        pop=Popup(title='Ảnh %d/%d'%(index[0]+1,len(photos)),content=outer,size_hint=(1,.96))
        def change(d):
            index[0]=(index[0]+d)%len(photos)
            viewer.source=self.thumbnail_path(photos[index[0]])
            pop.title='Ảnh %d/%d'%(index[0]+1,len(photos))
        nav.add_widget(btn('◀',lambda *_:change(-1)))
        nav.add_widget(btn('▶',lambda *_:change(1)))
        nav.add_widget(btn('Đóng',lambda *_:pop.dismiss()))
        outer.add_widget(nav);pop.open()

    def move(self,i,d):
        j=i+d
        if 0<=j<len(self.data['items']):
            a=self.data['items'];a[i],a[j]=a[j],a[i];self.save();self.last_pdf=None;self.render()

    def delete(self,i):
        outer=BoxLayout(orientation='vertical',padding=dp(12),spacing=dp(8))
        outer.add_widget(self.bubble_label('Xóa lỗi %d?'%(i+1)))
        row=BoxLayout(size_hint_y=None,height=dp(45),spacing=dp(5))
        pop=Popup(title='Xác nhận xóa',content=outer,size_hint=(.9,None),height=dp(185))
        row.add_widget(btn('Hủy',lambda *_:pop.dismiss()))
        def yes(*_):
            self.data['items'].pop(i);self.save();self.last_pdf=None;pop.dismiss();self.render()
        row.add_widget(btn('Xóa',yes,(.7,.25,.23,1)))
        outer.add_widget(row);pop.open()

    def form_popup(self,title,fields,on_save,after_field=None,fullscreen=False):
        """Native TextInput controls; fullscreen editor contains no touch-blocking overlay."""
        outer=BoxLayout(orientation='vertical',spacing=dp(4),padding=dp(3))
        with outer.canvas.before:
            Color(.97,.985,1,1)
            bg=RoundedRectangle(pos=outer.pos,size=outer.size,radius=[dp(2)])
        outer.bind(pos=lambda w,v:setattr(bg,'pos',v),
                   size=lambda w,v:setattr(bg,'size',v))
        # The normal ScrollView can delay or cancel touches destined for TextInput.
        # Bars-only mode passes touches to fields immediately; scrolling is available
        # by dragging the thin right-hand scroll bar.
        scroll=ScrollView(do_scroll_x=False,bar_width=dp(9),
                          scroll_type=['bars'],bar_color=(.2,.5,.7,.9))
        panel=GridLayout(cols=1,size_hint_y=None,spacing=dp(6),
                         padding=[dp(5),dp(4),dp(8),dp(10)])
        panel.bind(minimum_height=panel.setter('height'))
        inputs={}
        for key,caption,value,multi in fields:
            label=Label(text=caption,font_name=FONT,font_size='12sp',bold=True,
                        color=(.12,.27,.37,1),halign='left',valign='middle',
                        size_hint_y=None,height=dp(23))
            label.bind(width=lambda w,v:setattr(w,'text_size',(v,None)))
            panel.add_widget(label)
            inp=field(value,caption,multi)
            panel.add_widget(inp)
            inputs[key]=inp
            if after_field is not None:
                after_field(key,panel)
        scroll.add_widget(panel)
        outer.add_widget(scroll)
        footer=BoxLayout(size_hint_y=None,height=dp(48),spacing=dp(6))
        if fullscreen:
            # ModalView has no Popup title row and consumes the entire window.
            # Crucially, no FloatLayout/stencil intercepts TextInput touches.
            popup=ModalView(size_hint=(1,1),auto_dismiss=False,
                            background='',background_color=(0,0,0,0))
            popup.add_widget(outer)
        else:
            popup=Popup(title='',separator_height=0,content=outer,
                        size_hint=(1,1),auto_dismiss=False,
                        background='',background_color=(0,0,0,0))
        def close_it(*_):
            for inp in inputs.values():inp.focus=False
            popup.dismiss()
        def save_it(*_):
            values={k:v.text.strip() for k,v in inputs.items()}
            try:ok=on_save(values)
            except Exception as exc:
                self.notify('Không lưu được: '+str(exc)[:140]);return
            if ok:close_it()
        # Compact action icons with accessible touch targets.
        footer.add_widget(Widget())
        cancel=icon_btn('×',close_it,width=46,height=46,color=(.43,.49,.54,1))
        footer.add_widget(cancel)
        save_button=Button(text='✓',font_name=FONT,font_size='23sp',bold=True,
                           color=(.05,.48,.36,1),background_normal='',
                           background_color=(0,0,0,0),size_hint=(None,None),size=(dp(52),dp(46)))
        save_button.bind(on_release=save_it)
        footer.add_widget(save_button)
        outer.add_widget(footer)
        # Do not programmatically steal focus or reposition the dialog.
        return popup,panel,inputs

    def header(self):
        specs=[('basis','Căn cứ'),('inspector','Tên người kiểm tra'),
               ('owner','Chủ đầu tư'),('board','Ban QLDA'),('project','Dự án'),
               ('contractor','Kính gửi'),('package','Gói thầu'),
               ('section','Hạng mục'),('contract','Hợp đồng số'),
               ('inspection_date','Ngày kiểm tra'),('inspection_round','Đợt kiểm tra'),
               ('location','Địa danh'),('deadline','Hạn khắc phục chung'),
               ('signature_name','Họ tên người ký'),('signature_date','Ngày ký (để trống: hôm nay)'),
               ('signature_path','Đường dẫn ảnh chữ ký (tùy chọn)'),
               ('attachment_note','Đính kèm')]
        def save(values):
            self.data.update(values);self.save();self.last_pdf=None;return True
        pop,_,_=self.form_popup('Thông tin hồ sơ',[(k,n,self.data.get(k,''),False) for k,n in specs],save)
        pop.open()

    def edit_item(self,index=None):
        fresh=index is None
        item={'id':str(uuid.uuid4()),'position':'',
              'content':self.compose.text if fresh else '',
              'action':'','deadline':'','severity':'Trung bình',
              'photos':list(self.pending) if fresh else []}
        if not fresh:
            item=dict(self.data['items'][index])
            item['photos']=list(item.get('photos',[]))
        fields=[(k,n,item.get(k,''),multi) for k,n,multi in [
            ('position','Vị trí / hạng mục',False),
            ('content','Nội dung lỗi',True),
            ('action','Yêu cầu khắc phục',True),
            ('deadline','Thời hạn',False)]]
        severity_buttons=[]
        original_level=item.get('severity') or 'Trung bình'
        if original_level not in ('Cao','Trung bình','Thấp'):
            original_level='Trung bình'
        group_id='punch_level_'+uuid.uuid4().hex

        def append_level_after_content(key,panel):
            if key != 'content':
                return
            heading=lbl('Mức độ',12,True,24)
            panel.add_widget(heading)
            row=BoxLayout(size_hint_y=None,height=dp(39),spacing=dp(5))
            colors_by_level={
                'Cao':(.68,.22,.19,1),
                'Trung bình':(.67,.42,.10,1),
                'Thấp':(.15,.47,.35,1)
            }
            for value in ('Cao','Trung bình','Thấp'):
                button=ToggleButton(text=value,group=group_id,
                    allow_no_selection=False,
                    font_name=FONT,font_size='12sp',
                    state='down' if value==original_level else 'normal',
                    background_normal='',background_down='',
                    size_hint_y=None,height=dp(39))
                def update_button(w,st,tint=colors_by_level[value]):
                    w.background_color=tint if st=='down' else (.92,.95,.97,1)
                    w.color=(1,1,1,1) if st=='down' else (.16,.25,.35,1)
                button.bind(state=update_button)
                update_button(button,button.state)
                severity_buttons.append(button)
                row.add_widget(button)
            panel.add_widget(row)

        def save(values):
            values['severity']=next((b.text for b in severity_buttons
                                     if b.state=='down'),original_level)
            if not values['content']:
                self.notify('Cần nhập nội dung lỗi');return False
            item.update(values)
            if fresh:
                self.data['items'].append(item)
            else:
                self.data['items'][index]=item
            self.save()
            self.last_pdf=None
            if fresh:
                self.compose.text=''
                self.pending.clear()
            self.render()
            return True
        pop,panel,_=self.form_popup('Tin nhắn lỗi',fields,save,
                                     after_field=append_level_after_content,
                                     fullscreen=True)
        count=lbl('',12,height=30)
        panel.add_widget(count)
        # Gallery thumbnails only. Long-press a photo to confirm removal.
        gallery=GridLayout(cols=3,size_hint_y=None,spacing=dp(5))
        gallery.bind(minimum_height=gallery.setter('height'))
        panel.add_widget(gallery)
        def confirm_remove(n):
            if not (0<=n<len(item['photos'])):
                return
            content=BoxLayout(orientation='vertical',padding=dp(10),spacing=dp(8))
            content.add_widget(lbl('Xóa ảnh đã chọn khỏi lỗi này?',12,height=46))
            actions=BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(7))
            dialog=Popup(title='Xóa ảnh',content=content,size_hint=(.86,None),height=dp(190))
            actions.add_widget(btn('Hủy',lambda *_:dialog.dismiss(),height=42))
            def delete_now(*_):
                if 0<=n<len(item['photos']):
                    item['photos'].pop(n)
                dialog.dismiss()
                refresh()
            actions.add_widget(btn('Xóa ảnh',delete_now,(.72,.26,.25,1),42))
            content.add_widget(actions)
            dialog.open()
        def refresh():
            photos=item['photos']
            count.text='Ảnh đính kèm: %d  •  Nhấn giữ ảnh để xóa'%len(photos)
            gallery.clear_widgets()
            for i,path in enumerate(photos):
                source=self.thumbnail_path(path) if os.path.isfile(path) else ''
                photo=PhotoTap(source=source,size_hint_y=None,height=dp(102),fit_mode='cover')
                photo.tap_callback=lambda n=i:self.preview_photos(item['photos'],n)
                photo.long_press_callback=lambda n=i:confirm_remove(n)
                gallery.add_widget(photo)
        row=BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(5))
        row.add_widget(icon_btn('＋',lambda *_:self.pick_images(item['photos'],refresh),width=45,height=42))
        view_button=icon_btn('✎',lambda *_:self.preview_photos(item['photos']),width=45,height=42)
        row.add_widget(view_button)
        row.add_widget(Widget())
        panel.add_widget(row)
        refresh()
        pop.open()

    def _android_activity(self):
        from jnius import autoclass
        return autoclass('org.kivy.android.PythonActivity').mActivity

    def _save_direct_download(self, source):
        """Thử ghi trực tiếp. Chỉ báo thành công nếu tệp thực sự tồn tại."""
        folder = '/storage/emulated/0/Download' if platform == 'android' else os.path.join(os.path.expanduser('~'), 'Downloads')
        os.makedirs(folder, exist_ok=True)
        target = os.path.join(folder, os.path.basename(source))
        shutil.copyfile(source, target)
        if os.path.getsize(target) != os.path.getsize(source):
            raise IOError('Dung lượng tệp đã lưu không khớp')
        return target

    def _save_mediastore_fallback(self, source):
        """Android Downloads via content URI, avoiding MediaStore.Downloads and is_pending."""
        from jnius import autoclass, jarray
        Uri=autoclass('android.net.Uri')
        Values=autoclass('android.content.ContentValues')
        activity=self._android_activity()
        resolver=activity.getContentResolver()
        values=Values()
        values.put('display_name',str(os.path.basename(source)))
        values.put('mime_type','application/pdf')
        values.put('relative_path','Download/')
        collection=Uri.parse('content://media/external_primary/downloads')
        uri=resolver.insert(collection,values)
        if uri is None:raise IOError('Android từ chối tạo tệp Downloads')
        try:
            stream=resolver.openOutputStream(uri)
            if stream is None:raise IOError('Không mở được tệp PDF đích')
            try:
                with open(source,'rb') as f:
                    while True:
                        block=f.read(32768)
                        if not block:break
                        stream.write(jarray('b')([b if b<128 else b-256 for b in block]))
                stream.flush()
            finally:stream.close()
            return 'Downloads/'+os.path.basename(source)
        except Exception:
            resolver.delete(uri,None,None)
            raise

    def save_pdf_as(self):
        """Chọn thư mục và nhớ đường dẫn. Chỉ lưu khi người dùng bấm xác nhận."""
        if not getattr(self,'last_pdf',None):
            self.notify('Hãy bấm Xem PDF để tạo bản PDF trước.');return
        source=self.last_pdf[0]
        if not os.path.isfile(source):
            self.notify('Không tìm thấy PDF nội bộ');return
        if platform == 'android':
            try:
                from android_files import get_file_bridge
                bridge = get_file_bridge(self)
                if bridge is not None and bridge.save_pdf(source):
                    return
            except Exception as exc:
                print('Android document saver unavailable:', exc)
        initial=self.settings.get('last_pdf_dir','/storage/emulated/0/Download')
        if not os.path.isdir(initial):
            initial='/storage/emulated/0/Download' if os.path.isdir('/storage/emulated/0/Download') else self.root_dir
        outer=BoxLayout(orientation='vertical',spacing=dp(5),padding=dp(6))
        tip=lbl('Chọn thư mục lưu PDF (ghi nhớ cho lần sau)',12,True,32)
        outer.add_widget(tip)
        chooser=FileChooserListView(path=initial,dirselect=True,filters=[])
        outer.add_widget(chooser)
        filename=field(os.path.basename(source),'Tên file PDF')
        outer.add_widget(filename)
        row=BoxLayout(size_hint_y=None,height=dp(46),spacing=dp(5))
        pop=Popup(title='Lưu PDF vào thư mục...',content=outer,size_hint=(.98,.95))
        def do_save(*_):
            folder=chooser.path
            if chooser.selection and os.path.isdir(chooser.selection[0]):
                folder=chooser.selection[0]
            name=os.path.basename(filename.text.strip())
            if not name:name=os.path.basename(source)
            if not name.lower().endswith('.pdf'):name+='.pdf'
            target=os.path.join(folder,name)
            try:
                if os.path.abspath(target)!=os.path.abspath(source):
                    shutil.copyfile(source,target)
                if os.path.getsize(target)!=os.path.getsize(source):
                    raise IOError('Dung lượng PDF lưu không khớp')
                self.remember('last_pdf_dir',folder)
                self.last_saved_pdf=target
                pop.dismiss()
                self.notify('Đã lưu PDF thành công:\n'+target)
            except Exception as exc:
                self.notify('Không thể ghi vào thư mục này:\n'+str(exc)[:150]+
                    '\nHãy chọn thư mục khác hoặc cấp quyền bộ nhớ cho ứng dụng.')
        row.add_widget(btn('Hủy',lambda *_:pop.dismiss()))
        row.add_widget(btn('Lưu tại đây',do_save,(.05,.52,.36,1)))
        outer.add_widget(row)
        pop.open()

    def _android_pdf_uri(self, path):
        """Try installed FileProvider authorities; otherwise file URI fallback."""
        from jnius import autoclass
        Uri=autoclass('android.net.Uri')
        File=autoclass('java.io.File')
        activity=self._android_activity()
        provider=autoclass('androidx.core.content.FileProvider')
        package=activity.getPackageName()
        # Pydroid variants may expose different provider authorities.
        for authority in (package+'.fileprovider',package+'.provider',package+'.android.fileprovider'):
            try:
                uri=provider.getUriForFile(activity,authority,File(path))
                if uri:return uri,True
            except Exception:pass
        return Uri.fromFile(File(path)),False

    def open_pdf(self):
        """Use an installed Android PDF viewer, not PyMuPDF."""
        if not getattr(self,'last_pdf',None):
            self.notify('Hãy bấm PDF A4 để tạo tài liệu trước.');return
        path=self.last_pdf[0]
        if not os.path.isfile(path):
            self.notify('Không tìm thấy PDF: '+path);return
        if platform!='android':
            import webbrowser
            webbrowser.open('file://'+os.path.abspath(path));return
        try:
            from jnius import autoclass
            Intent=autoclass('android.content.Intent')
            activity=self._android_activity()
            uri,granted=self._android_pdf_uri(path)
            intent=Intent(Intent.ACTION_VIEW)
            intent.setDataAndType(uri,'application/pdf')
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            if granted:intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            # File URI may be rejected on newer Android; do not crash the app.
            activity.startActivity(Intent.createChooser(intent,'Chọn ứng dụng xem PDF'))
        except Exception as e:
            self.notify('Android chưa cho phép mở PDF từ ứng dụng.\n'
                        'Có thể dùng Lưu PDF để đưa tệp vào Downloads, rồi mở bằng My Files.\n'
                        'Chi tiết: '+str(e)[:150])

    def _render_android_pdf_page(self,path,page_number):
        """Android PdfRenderer co san, khong can pip install pymupdf.
        Ghi PNG cache trong du lieu app, khong dung MediaStore hay FileProvider.
        """
        from jnius import autoclass
        File=autoclass('java.io.File')
        ParcelFileDescriptor=autoclass('android.os.ParcelFileDescriptor')
        PdfRenderer=autoclass('android.graphics.pdf.PdfRenderer')
        Bitmap=autoclass('android.graphics.Bitmap')
        Config=autoclass('android.graphics.Bitmap$Config')
        FileOutputStream=autoclass('java.io.FileOutputStream')
        CompressFormat=autoclass('android.graphics.Bitmap$CompressFormat')
        fd=ParcelFileDescriptor.open(File(path),ParcelFileDescriptor.MODE_READ_ONLY)
        renderer=None;page=None;bitmap=None
        try:
            renderer=PdfRenderer(fd)
            count=renderer.getPageCount()
            if not (0<=page_number<count):raise IndexError('Trang PDF khong ton tai')
            page=renderer.openPage(page_number)
            scale=min(1.55,1000.0/max(1,page.getWidth()))
            w=max(1,int(page.getWidth()*scale));h=max(1,int(page.getHeight()*scale))
            bitmap=Bitmap.createBitmap(w,h,Config.ARGB_8888)
            bitmap.eraseColor(-1)
            page.render(bitmap,None,None,1)
            dest=os.path.join(self.root_dir,'preview_page_%d.png'%page_number)
            stream=FileOutputStream(dest)
            try:
                if not bitmap.compress(CompressFormat.PNG,100,stream):
                    raise IOError('Khong tao duoc anh xem truoc PDF')
                stream.flush()
            finally:stream.close()
            return dest,count
        finally:
            if page is not None:page.close()
            if bitmap is not None:bitmap.recycle()
            if renderer is not None:renderer.close()
            fd.close()

    def preview_pdf(self):
        if not getattr(self,'last_pdf',None):
            self.notify('Chua co PDF de xem.');return
        path=self.last_pdf[0]
        if not os.path.isfile(path):
            self.notify('Khong tim thay PDF.');return
        if platform!='android':
            self.open_pdf();return
        outer=BoxLayout(orientation='vertical',spacing=dp(4),padding=dp(4))
        sc=ScrollView(do_scroll_x=False)
        preview=Image(size_hint_y=None,allow_stretch=True,keep_ratio=True)
        sc.add_widget(preview);outer.add_widget(sc)
        state=[0,1]
        nav=BoxLayout(size_hint_y=None,height=dp(43),spacing=dp(6))
        pop=Popup(title='Xem PDF',content=outer,size_hint=(1,1),auto_dismiss=True)
        counter=Label(text='',font_name=FONT,size_hint_x=.6)
        def show(n):
            self._pdf_page_token+=1
            token=self._pdf_page_token
            counter.text='Đang tải...'
            def worker():
                try:
                    image_path,count=self._render_android_pdf_page(path,n)
                    with PILImage.open(image_path) as im:
                        ratio=im.height/max(1,im.width)
                    def ready(dt):
                        if token!=self._pdf_page_token:return
                        state[:]=[n,count]
                        preview.source=image_path
                        preview.reload()
                        preview.height=max(dp(300),sc.width*ratio)
                        counter.text='%d / %d'%(n+1,count)
                        sc.scroll_y=1
                    Clock.schedule_once(ready,0)
                except Exception as exc:
                    msg=str(exc)[:200]
                    Clock.schedule_once(lambda dt:self.notify('Không xem được PDF: '+msg),0)
            threading.Thread(target=worker,daemon=True).start()
        nav.add_widget(btn('‹',lambda *_:show(max(0,state[0]-1)),height=40))
        nav.add_widget(counter)
        nav.add_widget(btn('›',lambda *_:show(min(state[1]-1,state[0]+1)),height=40))
        nav.add_widget(btn('Luu...',lambda *_:(pop.dismiss(),self.save_pdf_as()),height=40))
        outer.add_widget(nav)
        pop.open()
        Clock.schedule_once(lambda dt:show(0),.1)

    def export_pdf(self):
        if not self.data['items']:
            self.notify('Chưa có lỗi để xuất');return
        if self._pdf_busy:
            self.notify('PDF đang được tạo, vui lòng chờ.');return
        if not os.path.isfile(FONT):
            self.notify('Thiếu file DejaVuSans.ttf cạnh main.py');return
        self._pdf_busy=True
        snapshot=copy.deepcopy(self.data)
        out=os.path.join(self.root_dir,'exports')
        os.makedirs(out,exist_ok=True)
        path=os.path.join(out,'PunchList_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.pdf')
        def worker():
            try:
                make_pdf(path,snapshot)
                if not os.path.isfile(path) or os.path.getsize(path)==0:
                    raise RuntimeError('PDF chưa tạo thành công')
                def ready(dt):
                    self._pdf_busy=False
                    self.last_pdf=(path,None)
                    self.preview_pdf()
                Clock.schedule_once(ready,0)
            except Exception as e:
                detail=traceback.format_exc()
                try:
                    with open(os.path.join(self.root_dir,'loi_pdf.txt'),'w',encoding='utf-8') as f:
                        f.write(detail)
                except OSError:pass
                msg=str(e)[:140]
                def failed(dt):
                    self._pdf_busy=False
                    self.notify('Xuất PDF lỗi: '+msg)
                Clock.schedule_once(failed,0)
        threading.Thread(target=worker,daemon=True).start()


def make_pdf(path, data):
    """Export using the administrative PDF form from desktop Punch List v2."""
    from pdf_form_v2 import build_pdf
    return build_pdf(path, data, FONT)


if __name__=='__main__':
    DefectApp().run()
