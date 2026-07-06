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
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Extensão de isolação do player + assets (logo).
_datas = [('player_ext', 'player_ext'), ('assets', 'assets')]
if os.path.exists('config.json'):
    _datas.append(('config.json', '.'))

_icon = 'assets/logo.ico' if os.path.exists('assets/logo.ico') else None

# curl_cffi traz um libcurl compilado (necessário p/ passar pelo Cloudflare/TLS).
_cc_datas, _cc_binaries, _cc_hidden = collect_all('curl_cffi')
_datas += _cc_datas

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=_cc_binaries,
    datas=_datas,
    hiddenimports=[
        'player_webview',
        'curl_cffi',
        'PySide6.QtNetwork',
    ] + _cc_hidden,
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
    icon=_icon,
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
