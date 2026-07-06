# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec para o APlayer
# Build:  pyinstaller build.spec
#
# Observações:
#  - A reprodução usa o Edge WebView2 (já presente no Windows), via pywebview.
#    Não é necessário empacotar QtWebEngine.
#  - player_webview.py é importado de forma tardia (modo --play); por isso
#    entra explicitamente em hiddenimports.

import os

block_cipher = None

_datas = []
if os.path.exists('config.json'):
    _datas.append(('config.json', '.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        'player_webview',
        'webview',
        'webview.platforms.edgechromium',
        'clr_loader',
        'pythonnet',
        'requests',
        'PySide6.QtNetwork',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'tkinter',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove entradas None de datas
a.datas = [d for d in a.datas if d[0] is not None]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='APlayer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='APlayer',
)
