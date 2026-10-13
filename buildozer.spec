[app]
title = Space Exploration
package.name = spaceexploration
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 0.2.0

# ⚠️ ВАЖНО: Python 3.10 для совместимости с Pygame
requirements = python3==3.10.10, pygame-ce==2.5.5

orientation = landscape
fullscreen = 1
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True

# Разрешения (для сохранения сейвов)
android.permissions = WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# Иконка и заставка (позже добавим)
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

[buildozer]
log_level = 2
warn_on_root = 1
