[app]
title = Punch List Bãi Xép
package.name = punchlist
package.domain = vn.baixep
source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,ttf,kv,json
source.exclude_dirs = .git,.github,bin,.buildozer,__pycache__,tests
version = 38.0.1
requirements = python3,kivy==2.3.1,pillow,reportlab==4.5.1,pyjnius
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png
# arm64 phù hợp máy Samsung A34 và đa số máy Android mới.
android.archs = arm64-v8a
android.api = 35
android.minapi = 24
android.ndk = 28c
android.accept_sdk_license = True
android.allow_backup = False
# Sử dụng Android Storage Access Framework. Không cần quyền toàn bộ bộ nhớ.
# android.permissions =

[buildozer]
log_level = 2
warn_on_root = 1
