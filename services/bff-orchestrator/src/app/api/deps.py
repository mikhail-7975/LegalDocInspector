from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from starlette import status

from configs.config import AppConfig, load_yaml_config

from app.config import Settings, get_settings


def _ensure_legacy_path(root: Path) -> None:
    rs = str(root.resolve())
    if rs not in sys.path:
        sys.path.insert(0, rs)


def load_app_config(settings: Settings) -> AppConfig:
    _ensure_legacy_path(settings.legacy_repo_root)
    path = settings.config_yaml
    if not path.is_absolute():
        path = settings.legacy_repo_root / path
    cfg = load_yaml_config(str(path))
    root = settings.legacy_repo_root
    cfg.claim_template_path = str(root / cfg.claim_template_path)
    cfg.calculation_claim_template_path = str(root / cfg.calculation_claim_template_path)
    cfg.save_data_folder = str(root / cfg.save_data_folder)
    return cfg


def get_app_config(settings: Settings = Depends(get_settings)) -> AppConfig:
    return load_app_config(settings)


def require_session_user(request: Request) -> str:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется вход")
    return str(user)


LegacyConfig = Annotated[AppConfig, Depends(get_app_config)]
CurrentUser = Annotated[str, Depends(require_session_user)]
