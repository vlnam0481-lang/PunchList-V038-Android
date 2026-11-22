# -*- coding: utf-8 -*-
"""Android SAF bridge for a standalone Kivy APK (no storage permission needed).

Select multiple images with ACTION_OPEN_DOCUMENT, copy content:// URIs to
private app image storage, and save PDFs with ACTION_CREATE_DOCUMENT.
Falls back to the original file chooser outside python-for-android.
"""
import os
import shutil
import uuid
import threading
from kivy.clock import Clock

_SINGLETON = None


def get_file_bridge(app):
    global _SINGLETON
    try:
        from android import activity
        from jnius import autoclass
    except ImportError:
        return None
    if _SINGLETON is None or _SINGLETON.app is not app:
        _SINGLETON = AndroidFileBridge(app, activity, autoclass)
    return _SINGLETON


class AndroidFileBridge:
    PICK_REQUEST = 7810
    SAVE_REQUEST = 7811
    MAX_IMAGE_SIZE = 50 * 1024 * 1024

    def __init__(self, app, activity, autoclass):
        self.app = app
        self.activity_events = activity
        self.autoclass = autoclass
        self.java_activity = autoclass('org.kivy.android.PythonActivity').mActivity
        self.Intent = autoclass('android.content.Intent')
        self.pending_images = None
        self.pending_pdf = None
        self.activity_events.bind(on_activity_result=self._on_activity_result)

    def _launch(self, intent, code):
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def start():
            self.java_activity.startActivityForResult(intent, code)
        start()

    def pick_images(self, target, done):
        try:
            intent = self.Intent(self.Intent.ACTION_OPEN_DOCUMENT)
            intent.addCategory(self.Intent.CATEGORY_OPENABLE)
            intent.setType('image/*')
            intent.putExtra(self.Intent.EXTRA_ALLOW_MULTIPLE, True)
            intent.addFlags(self.Intent.FLAG_GRANT_READ_URI_PERMISSION)
            self.pending_images = (target, done)
            self._launch(intent, self.PICK_REQUEST)
            return True
        except Exception:
            self.pending_images = None
            raise

    def save_pdf(self, source):
        if not os.path.isfile(source):
            raise FileNotFoundError(source)
        intent = self.Intent(self.Intent.ACTION_CREATE_DOCUMENT)
        intent.addCategory(self.Intent.CATEGORY_OPENABLE)
        intent.setType('application/pdf')
        intent.putExtra(self.Intent.EXTRA_TITLE, os.path.basename(source))
        intent.addFlags(self.Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
        self.pending_pdf = source
        self._launch(intent, self.SAVE_REQUEST)
        return True

    def _on_activity_result(self, request_code, result_code, intent):
        if request_code not in (self.PICK_REQUEST, self.SAVE_REQUEST):
            return
        # Result from Android activity can be on a Java thread.
        Clock.schedule_once(
            lambda dt: self._process_result(request_code, result_code, intent), 0)

    def _process_result(self, request_code, result_code, intent):
        if request_code == self.PICK_REQUEST:
            pending = self.pending_images
            self.pending_images = None
            if not pending or result_code != -1 or intent is None:
                return
            target, done = pending
            uris = []
            try:
                clip = intent.getClipData()
                if clip is not None:
                    for index in range(clip.getItemCount()):
                        uris.append(clip.getItemAt(index).getUri())
                elif intent.getData() is not None:
                    uris.append(intent.getData())
            except Exception as exc:
                self.app.notify('Không lấy được ảnh đã chọn: ' + str(exc)[:130])
                return
            if not uris:
                return
            def worker():
                saved, errors = [], []
                for uri in uris:
                    try:
                        saved.append(self._copy_image_from_uri(uri))
                    except Exception as exc:
                        errors.append(str(exc)[:90])
                def ready(dt):
                    target.extend(saved)
                    if saved:
                        try: done()
                        except Exception as exc: self.app.notify('Không cập nhật được ảnh: ' + str(exc)[:120])
                    if errors:
                        self.app.notify('Một số ảnh không nhập được: ' + errors[0])
                Clock.schedule_once(ready, 0)
            threading.Thread(target=worker, daemon=True).start()

        elif request_code == self.SAVE_REQUEST:
            source = self.pending_pdf
            self.pending_pdf = None
            if source is None or result_code != -1 or intent is None:
                return
            uri = intent.getData()
            if uri is None:
                self.app.notify('Android không trả về vị trí lưu PDF.')
                return
            def worker():
                try:
                    self._copy_pdf_to_uri(source, uri)
                    def ok(dt):
                        try:
                            self.app.remember('last_pdf_uri', str(uri))
                        except Exception: pass
                        self.app.notify('Đã lưu PDF vào vị trí đã chọn trong Android.\n'
                                        + os.path.basename(source))
                    Clock.schedule_once(ok, 0)
                except Exception as exc:
                    Clock.schedule_once(
                        lambda dt, msg=str(exc): self.app.notify(
                            'Không lưu được PDF: ' + msg[:160]), 0)
            threading.Thread(target=worker, daemon=True).start()

    def _copy_image_from_uri(self, uri):
        resolver = self.java_activity.getContentResolver()
        mime = str(resolver.getType(uri) or '').lower()
        ext = {'image/jpeg':'.jpg', 'image/png':'.png',
               'image/webp':'.webp', 'image/bmp':'.bmp'}.get(mime,'.jpg')
        dest = os.path.join(self.app.images_dir, uuid.uuid4().hex + ext)
        pfd = resolver.openFileDescriptor(uri, 'r')
        if pfd is None:
            raise OSError('Không đọc được ảnh từ Android')
        try:
            # Duplicate FD so closing Python's handle doesn't close the Java FD.
            with os.fdopen(os.dup(pfd.getFd()), 'rb') as inf, open(dest, 'wb') as out:
                total = 0
                while True:
                    block = inf.read(256*1024)
                    if not block:
                        break
                    total += len(block)
                    if total > self.MAX_IMAGE_SIZE:
                        raise ValueError('Ảnh vượt 50 MB')
                    out.write(block)
            if total == 0:
                raise ValueError('Ảnh trống')
            return dest
        except Exception:
            try: os.remove(dest)
            except OSError: pass
            raise
        finally:
            pfd.close()

    def _copy_pdf_to_uri(self, source, uri):
        pfd = self.java_activity.getContentResolver().openFileDescriptor(uri, 'w')
        if pfd is None:
            raise OSError('Không có quyền ghi vào nơi lưu PDF')
        try:
            with open(source, 'rb') as inf, os.fdopen(os.dup(pfd.getFd()), 'wb') as out:
                shutil.copyfileobj(inf, out, 256*1024)
                out.flush()
        finally:
            pfd.close()
