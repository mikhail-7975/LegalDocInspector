"""
Регистрация встроенных плагинов docling в frozen-сборке (PyInstaller).

В exe setuptools entrypoints не работают — фабрики OCR/layout/picture остаются пустыми.
"""

from __future__ import annotations

import sys

_bootstrapped = False


def ensure_docling_plugins() -> None:
    global _bootstrapped
    if _bootstrapped or not getattr(sys, "frozen", False):
        return

    from docling.models.factories.base_factory import BaseFactory
    from docling.models.plugins import defaults

    _orig_load = BaseFactory.load_from_plugins

    def _load_from_plugins_with_defaults(
        self,
        plugin_name: str | None = None,
        allow_external_plugins: bool = False,
    ) -> None:
        _orig_load(self, plugin_name, allow_external_plugins)
        loader = {
            "picture_description": defaults.picture_description,
            "ocr_engines": defaults.ocr_engines,
            "layout_engines": defaults.layout_engines,
            "table_structure_engines": defaults.table_structure_engines,
        }.get(self.plugin_attr_name)
        if not loader:
            return
        try:
            self.process_plugin(
                loader(),
                "docling",
                "docling.models.plugins.defaults",
            )
        except ValueError:
            pass

    BaseFactory.load_from_plugins = _load_from_plugins_with_defaults  # type: ignore[method-assign]

    from docling.models import factories as factories_mod

    for getter in (
        factories_mod.get_ocr_factory,
        factories_mod.get_picture_description_factory,
        factories_mod.get_layout_factory,
        factories_mod.get_table_structure_factory,
    ):
        if hasattr(getter, "cache_clear"):
            getter.cache_clear()

    _bootstrapped = True
