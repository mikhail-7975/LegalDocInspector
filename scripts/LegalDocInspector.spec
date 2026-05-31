# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec: точка входа scripts/run_dev.py
# Запуск сборки: python scripts/build_exe.py

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

ROOT = Path(SPECPATH).resolve().parent
COLLECT_NAME = os.environ.get("LDI_COLLECT_NAME", "LegalDocInspector")
ENTRY = ROOT / "scripts" / "run_dev.py"

# Не тянуть тестовые пакеты (collect_all('pandas') добавляет тысячи модулей и час сборки)
EXCLUDES = [
    "pandas.tests",
    "numpy.tests",
    "scipy.tests",
    "pytest",
    "bs4.tests",
    "tornado.test",
    "IPython",
    "jupyter",
    "notebook",
    "matplotlib.tests",
]

datas: list = [
    (str(ROOT / "LegalDocInspector" / "streamlit"), "LegalDocInspector/streamlit"),
    (str(ROOT / ".streamlit"), ".streamlit"),
]
binaries: list = []
hiddenimports: list = [
    "LegalDocInspector.legal_doc_inspector.docling_artifacts",
    "LegalDocInspector.legal_doc_inspector.docling_frozen_bootstrap",
    "LegalDocInspector.backend",
    "LegalDocInspector.backend.routes",
    "LegalDocInspector.legal_doc_inspector.exel_parser",
    "LegalDocInspector.legal_doc_inspector.pdf_parser.parser_models",
    "LegalDocInspector.legal_doc_inspector.utils.parse_egrul_sertificate",
    "LegalDocInspector.legal_doc_inspector.utils.parse_info_by_inn",
    "LegalDocInspector.legal_doc_inspector.doc_creator.claim_generator",
    "LegalDocInspector.legal_doc_inspector.doc_creator.calculation_claim_generator",
    "configs.config",
    "pymorphy3",
    "pymorphy3_dicts_ru",
    "streamlit.web.cli",
    "pandas",
    "openpyxl",
    "bs4",
    "rapidfuzz",
    "altair",
    "tornado",
    "torch",
    "docling",
    "docling_core",
    "docling_parse",
    "latex2mathml",
    "docling.models.plugins.defaults",
    "docling.models.stages.picture_description.picture_description_vlm_engine_model",
    "docling.models.stages.picture_description.picture_description_vlm_model",
    "docling.models.stages.picture_description.picture_description_api_model",
    "docling.models.stages.ocr.tesseract_ocr_cli_model",
    "docling.models.stages.ocr.tesseract_ocr_model",
    "docling.models.stages.layout.layout_model",
    "docling.models.stages.table_structure.table_structure_model",
]

# collect_all только для пакетов с данными/плагинами; не для pandas/torch
for pkg in (
    "streamlit",
    "flask",
    "docling",
    "docling_core",
    "docling_parse",
    "latex2mathml",
):
    try:
        tmp = collect_all(pkg)
        datas += tmp[0]
        binaries += tmp[1]
        hiddenimports += tmp[2]
    except Exception:
        pass

hiddenimports += collect_submodules("LegalDocInspector")

for _docling_sub in (
    "docling.models",
    "docling.models.stages",
    "docling.models.stages.picture_description",
    "docling.models.stages.ocr",
    "docling.models.stages.layout",
    "docling.models.stages.table_structure",
    "docling.pipeline",
):
    try:
        hiddenimports += collect_submodules(_docling_sub)
    except Exception:
        pass

_runtime_hook = str(ROOT / "scripts" / "pyi_rth_docling.py")

a = Analysis(
    [str(ENTRY)],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[_runtime_hook] if Path(_runtime_hook).is_file() else [],
    excludes=EXCLUDES,
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
    name="LegalDocInspector",
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=COLLECT_NAME,
)
