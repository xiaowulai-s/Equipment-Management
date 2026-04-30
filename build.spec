# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller配置文件
用于将工业设备管理系统打包为独立可执行文件
"""

import sys
import os

block_cipher = None

a = Analysis(
    ['main.py'],  # 入口文件
    pathex=[],
    binaries=[],
    datas=[
        # 包含配置文件
        ('config.json', '.'),
        ('config/default_config.json', 'config'),
        ('device_types.json', '.'),

        # 包含UI样式文件
        ('ui/styles', 'ui/styles'),

        # 包含资源文件（如果有）
        # ('assets/*', 'assets'),
    ],
    hiddenimports=[
        # PySide6相关
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtNetwork',

        # 数据库相关
        'sqlalchemy',
        'sqlalchemy.dialects.sqlite',

        # 串口通信
        'serial',
        'serial.tools',
        'serial.tools.list_ports',

        # 数据可视化
        'pyqtgraph',
        'numpy',

        # 项目模块
        'core',
        'core.protocols',
        'core.communication',
        'core.device',
        'core.data',
        'core.utils',
        'ui',
        'ui.widgets',
        'ui.styles',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块以减小体积
        'tkinter',
        'matplotlib',
        'pandas',
        'scipy',
        'IPython',
        'pytest',
        'unittest',
        'doctest',
    ],
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
    name='EquipmentManagement',  # 可执行文件名称
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 使用UPX压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以指定图标文件路径
)

# 如果需要生成目录模式（非单文件模式），取消注释以下代码
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name='EquipmentManagement',
# )
