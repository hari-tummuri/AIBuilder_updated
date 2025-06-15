# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, Tree
import os

pathex = [os.path.abspath('.')]

# Replace datas = [] with a list of Tree calls:
datas = [
    Tree('core', prefix='core'),
    Tree('itassist', prefix='itassist'),
    Tree('userdata', prefix='userdata'),
    Tree('Ollama', prefix='Ollama'),
]

# Next, set up hiddenimports (so PyInstaller bundles dynamic imports from transformers, Django, etc.):
hiddenimports = (
    collect_submodules('sentence_transformers') +
    collect_submodules('transformers') +
    ['django', 'django.core.asgi']
)

a = Analysis(
    ['start_backend.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
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
    name='start_backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='start_backend',
)
