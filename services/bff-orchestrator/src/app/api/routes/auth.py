from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from starlette import status

from app.config import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


def get_settings_dep() -> Settings:
    return get_settings()


@router.post("/login")
def login(
    body: LoginBody,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> dict[str, str]:
    if (
        body.username == settings.default_admin_user
        and body.password == settings.default_admin_password
    ):
        request.session["user"] = body.username
        return {"status": "ok", "user": body.username}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")


@router.post("/logout")
def logout(request: Request) -> dict[str, str]:
    request.session.clear()
    return {"status": "ok"}
