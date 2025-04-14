# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import platform

block_cipher = None

# 운영체제 확인
system = platform.system()

# 아이콘 경로 설정
if system == 'Darwin':  # macOS
    icon_path = os.path.join('build_resources', 'app_icon.icns')
elif system == 'Windows':
    icon_path = os.path.join('build_resources', 'app_icon.ico')
else:  # Linux 등
    icon_path = os.path.join('build_resources', 'app_icon.png')

# 데이터 파일 설정
datas = [
    ('config', 'config'),
    ('default_images_1', 'default_images_1'),
    ('default_images_2', 'default_images_2'),
    ('default_images_3', 'default_images_3'),
    ('default_images_4', 'default_images_4'),
    ('default_images_5', 'default_images_5'),
    ('default_images_6', 'default_images_6'),
    ('default_images_7', 'default_images_7'),
    ('default_images_8', 'default_images_8'),
    ('default_images_9', 'default_images_9'),
    ('default_images_10', 'default_images_10'),
    ('default_images_11', 'default_images_11')
]

# 실제 존재하는 데이터 디렉토리만 포함
filtered_datas = [(src, dst) for src, dst in datas if os.path.exists(src)]

# 분석 설정
a = Analysis(
    ['blog_writer_app.py'],
    pathex=[],
    binaries=[],
    datas=filtered_datas,
    hiddenimports=[
        'PIL', 
        'selenium', 
        'flet', 
        'webdriver_manager',
        'json', 
        'os', 
        'sys', 
        'time', 
        'datetime', 
        'random',
        'nltk',
        'konlpy',
        'openai',
        'flet.web',
        'flet.desktop'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 중복 라이브러리 처리
a.datas = list(dict(a.datas).items())

# PYZ 객체 생성
pyz = PYZ(
    a.pure, 
    a.zipped_data,
    cipher=block_cipher
)

# 실행 파일 생성
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
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path
)

# 컬렉션 생성
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='네이버블로그자동화',
)

# macOS 앱 번들 생성
if system == 'Darwin':
    app = BUNDLE(
        coll,
        name='네이버블로그자동화.app',
        icon=icon_path,
        bundle_identifier='com.liontkd.naverblogauto',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'NSRequiresAquaSystemAppearance': 'False',
            'CFBundleDisplayName': '네이버블로그자동화',
            'CFBundleName': '네이버블로그자동화',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'LSEnvironment': {
                'LANG': 'ko_KR.UTF-8',
                'LC_ALL': 'ko_KR.UTF-8',
                'LC_CTYPE': 'ko_KR.UTF-8'
            }
        }
    ) 