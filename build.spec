# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Axial Resolution GUI — single-file EXE.

Build with:  pyinstaller build.spec --clean
"""

import os

block_cipher = None

root = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(root, 'Axial_Resolution_Master.py')],
    pathex=[root],
    binaries=[
        (os.path.join(root, 'PlayerOneCamera.dll'), '.'),
    ],
    datas=[
        (os.path.join(root, 'config.yml'), '.'),
        (os.path.join(root, 'pyPOACamera.py'), '.'),
        (os.path.join(root, 'assets'), 'assets'),
    ],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'cv2',
        'numpy',
        'matplotlib',
        'matplotlib.backends.backend_tkagg',
        'pylablib',
        'pylablib.devices',
        'pylablib.devices.Thorlabs',
        'pylablib.devices.Thorlabs.base',
        'pypylon',
        'pypylon.pylon',
        'pypylon.genicam',
        'pytic',
        'axial_app',
        'axial_app.main',
        'axial_app.pages.capture_page',
        'axial_app.widgets',
        'axial_app.dialogs',
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

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AxialResolution',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(root, 'assets', 'app_icon.ico')
        if os.path.exists(os.path.join(root, 'assets', 'app_icon.ico'))
        else None,
)
