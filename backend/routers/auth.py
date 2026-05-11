# routers/auth.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse

import auth_pure
from deps import create_token, optional_user, optional_user_role
from schemas import AuthSetupRequest, AuthStatusResponse, LoginRequest

router = APIRouter()


@router.get("/status", response_model=AuthStatusResponse)
def auth_status():
    count = auth_pure.user_count()
    return AuthStatusResponse(
        authenticated=False,
        username=None,
        needs_setup=(count == 0),
        role=None,
    )


@router.get("/me", response_model=AuthStatusResponse)
def auth_me(user_role: tuple[str, str] | None = Depends(optional_user_role)):
    count = auth_pure.user_count()
    return AuthStatusResponse(
        authenticated=user_role is not None,
        username=user_role[0] if user_role else None,
        needs_setup=(count == 0),
        role=user_role[1] if user_role else None,
    )


@router.post("/login")
def login(req: LoginRequest, response: Response):
    if not auth_pure.check_credentials(req.username, req.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ungültige Anmeldedaten")

    role = auth_pure.get_role(req.username)
    token = create_token(req.username, role)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=8 * 3600,
    )
    return {"ok": True, "username": req.username, "role": role}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"ok": True}


@router.post("/setup", response_model=AuthStatusResponse)
def setup(req: AuthSetupRequest, response: Response):
    if auth_pure.user_count() > 0:
        raise HTTPException(status_code=400, detail="Admin-Konto bereits vorhanden")
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Benutzername und Passwort dürfen nicht leer sein")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Passwort muss mindestens 8 Zeichen lang sein")

    auth_pure.create_user(req.username, req.password, role="admin")
    token = create_token(req.username, "admin")
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=8 * 3600,
    )
    return AuthStatusResponse(authenticated=True, username=req.username, needs_setup=False, role="admin")
