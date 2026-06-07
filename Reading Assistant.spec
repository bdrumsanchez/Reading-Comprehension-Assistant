# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('assistant', 'assistant')]
binaries = []
hiddenimports = ['tiktoken', 'dotenv', 'pkg_resources']
tmp_ret = collect_all('PySide6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('openai')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

block_cipher = None

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['sentence_transformers', 'chromadb', 'torch', 'transformers'],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Reading Assistant',
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
    icon=['/Users/bert.sanchez/Reading Comprehension Assistant/build/AppIcon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Reading Assistant',
)
app = BUNDLE(
    coll,
    name='Reading Assistant.app',
    icon='/Users/bert.sanchez/Reading Comprehension Assistant/build/AppIcon.icns',
    bundle_identifier='com.readingassistant.app',
    info_plist={
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1',
        'CFBundleDisplayName': 'Reading Assistant',
        'CFBundleName': 'Reading Assistant',
        'CFBundleIdentifier': 'com.readingassistant.app',
        'CFBundlePackageType': 'APPL',
        'NSHighResolutionCapable': True,
        'NSUIElement': False,
        'LSBackgroundOnly': False,
        'CFBundleInfoDictionaryVersion': '6.0',
        'NSHumanReadableCopyright': 'Copyright © 2025',
    },
)
