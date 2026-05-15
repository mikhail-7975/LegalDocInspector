# PyInstaller runtime hook: docling plugins до импорта бэкенда
import sys

if getattr(sys, "frozen", False):
    try:
        from LegalDocInspector.legal_doc_inspector.docling_frozen_bootstrap import (
            ensure_docling_plugins,
        )

        ensure_docling_plugins()
    except Exception:
        pass
