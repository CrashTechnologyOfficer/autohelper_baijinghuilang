# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import rapidocr_openvino


block_cipher = None

package_name = 'rapidocr_openvino'
install_dir = Path(rapidocr_openvino.__file__).resolve().parent

onnx_paths = list(install_dir.rglob('*.onnx')) + list(install_dir.rglob('*.txt'))
yaml_paths = list(install_dir.rglob('*.yaml'))

onnx_add_data = [(str(v.parent), f'{package_name}/{v.parent.name}')
                 for v in onnx_paths]

yaml_add_data = []
for v in yaml_paths:
    if package_name == v.parent.name:
        yaml_add_data.append((str(v.parent / '*.yaml'), package_name))
    else:
        yaml_add_data.append(
            (str(v.parent / '*.yaml'), f'{package_name}/{v.parent.name}'))

import openvino

block_cipher = None

package_name = 'openvino'
install_dir = Path(openvino.__file__).resolve().parent

openvino_dll_path = list(install_dir.rglob('openvino_intel_cpu_plugin.dll')) + list(install_dir.rglob('openvino_onnx_frontend.dll'))


# Modified list comprehension with a condition check
openvino_add_data = [(str(v), f'{package_name}/{v.parent.name}')
                     for v in openvino_dll_path]

print(f'openvino_add_data {openvino_add_data}')
add_data = list(set(yaml_add_data + onnx_add_data + openvino_add_data))

excludes = ['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter', 'resources', 'matplotlib','numpy.lib']
add_data.append(('icon.ico', '.'))
print(f"add_data {add_data}")

a = Analysis(
    ['main_debug.py'],
    pathex=[],
    binaries=[],
    datas=add_data,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

import fnmatch

# List of patterns to exclude
exclude_patterns = ['opencv_videoio_ffmpeg',  'opengl32sw.dll']

# Optimized list comprehension using any() with a generator expression
a.binaries = [x for x in a.binaries if not any(pattern in x[0] for pattern in exclude_patterns)]

print(f'a.binaries {a.binaries}')

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ok-baijing-debug',
    icon='icon.ico',
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
    name='test',
)

