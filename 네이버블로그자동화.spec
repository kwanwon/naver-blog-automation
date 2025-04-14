# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['blog_writer_app.py'],
    pathex=[],
    binaries=[],
    datas=[('config', 'config'), ('default_images', 'default_images'), ('default_images_1', 'default_images_1'), ('default_images_2', 'default_images_2'), ('default_images_3', 'default_images_3'), ('default_images_4', 'default_images_4'), ('default_images_5', 'default_images_5'), ('default_images_6', 'default_images_6'), ('default_images_7', 'default_images_7'), ('default_images_8', 'default_images_8'), ('default_images_9', 'default_images_9'), ('default_images_10', 'default_images_10'), ('chromedriver', '.'), ('.env', '.'), ('naver_blog_auto.py', '.'), ('naver_blog_auto_image.py', '.'), ('naver_blog_post_finisher.py', '.'), ('modules', 'modules')],
    hiddenimports=['PIL', 'selenium', 'flet', 'webdriver_manager', 'json', 'os', 'sys', 'time', 'datetime', 'random', 'nltk', 'konlpy', 'openai'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='네이버블로그자동화',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['build_resources/app_icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='네이버블로그자동화',
)
app = BUNDLE(
    coll,
    name='네이버블로그자동화.app',
    icon='build_resources/app_icon.icns',
    bundle_identifier=None,
)
