# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

block_cipher = None

libtorrent_binaries = collect_dynamic_libs('libtorrent')
webview_binaries = collect_dynamic_libs('webview')
webview_datas = collect_data_files('webview')
pystray_hidden = collect_submodules('pystray')
pil_hidden = collect_submodules('PIL')


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=libtorrent_binaries + webview_binaries,
    datas=[
        ('frontend', 'frontend'),
        ('arcadia-extension', 'arcadia-extension'),
        ('assets', 'assets'),
        ('assets/icons/arcadia.ico', 'assets/icons'),
        ('frontend/favicon.ico', 'frontend'),
    ] + webview_datas,
    hiddenimports=[
        'libtorrent',
        'pythonnet',
        'clr_loader',
        'webview.platforms.winforms',
        'webview.platforms.edgechromium',
    ] + pystray_hidden + pil_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'pytest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Arcadia',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icons/arcadia.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Arcadia',
)
