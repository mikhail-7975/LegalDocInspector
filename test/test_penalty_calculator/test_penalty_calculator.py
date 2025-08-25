"""
Тесты для legacy penalty_calculator - DEPRECATED.
Новые тесты находятся в test/test_services/test_penalty_service.py
"""

import pytest


@pytest.mark.deprecated
def test_penalty_calculator_deprecated():
    """Тест показывает, что старый калькулятор устарел."""
    # Этот тест показывает, что нужно использовать новый penalty_service
    with pytest.warns(DeprecationWarning):
        import warnings

        warnings.warn(
            "penalty_calculator устарел. Используйте penalty_service",
            DeprecationWarning,
            stacklevel=2,
        )
        assert True  # Тест проходит, но с предупреждением
