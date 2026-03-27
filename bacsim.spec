# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

block_cipher = None

bacpypes3_datas, bacpypes3_binaries, bacpypes3_hiddenimports = collect_all("bacpypes3")


a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=bacpypes3_binaries,
    datas=[
        ('sample_projects', 'sample_projects'),
        ('docs', 'docs'),
        ('README.md', '.'),
        ('TERMS.md', '.'),
        ('LICENSE-COMMERCIAL.md', '.'),
    ] + bacpypes3_datas,
    hiddenimports=bacpypes3_hiddenimports,
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
    [],
    exclude_binaries=True,
    name='BACsim',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BACsim',
)
