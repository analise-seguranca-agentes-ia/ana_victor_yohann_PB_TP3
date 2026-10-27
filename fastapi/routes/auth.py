from datetime import timedelta

from database import get_session
from limiter import limiter
from models.auth import Token
from models.user import PostUserLoginRequest, PostUserRegisterRequest, User
from routes.responses import RESPONSE_422
from security.auth import (ACCESS_TOKEN_EXPIRE_MINUTES, authenticate_user,
                           create_access_token, get_hash_password, get_user)
from sqlmodel import Session

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post(
    "/token",
    response_model=Token,
    summary="Faz login e retorna o token JWT",
    description=(
        "Recebe `username` e `password` como formulário (OAuth2 password flow) e "
        "retorna um token JWT válido por 30 minutos, que deve ser enviado no header "
        "`Authorization: Bearer <token>` das rotas protegidas. "
        "Limite de **10 requisições por minuto** por cliente."
    ),
    responses={
        401: {
            "description": "Senha incorreta.",
            "content": {"application/json": {"example": {"detail": "Invalid credentials."}}},
        },
        404: {
            "description": "Usuário não encontrado.",
            "content": {"application/json": {"example": {"detail": "User could not be found."}}},
        },
        429: {
            "description": "Limite de 10 requisições por minuto excedido.",
            "content": {"application/json": {"example": {"error": "Rate limit exceeded: 10 per 1 minute"}}},
        },
        **RESPONSE_422,
    },
)
@limiter.limit("10/minute")
async def login_get_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
) -> Token:
    user = authenticate_user(
        PostUserLoginRequest(username=form_data.username, password=form_data.password),
        session,
    )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer")


@auth_router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um novo usuário",
    description=(
        "Rota pública. Cria um usuário com o perfil **default**. "
        "A senha é armazenada apenas como hash (Argon2). "
        "Campos além de `username` e `password` são rejeitados com 422."
    ),
    responses={
        201: {
            "description": "Usuário criado.",
            "content": {"application/json": {"example": {"detail": "User was successfully created."}}},
        },
        409: {
            "description": "O username já está em uso.",
            "content": {"application/json": {"example": {"detail": "Username is already in use."}}},
        },
        **RESPONSE_422,
    },
)
async def register_user(
    new_user: PostUserRegisterRequest = Body(),
    session: Session = Depends(get_session),
):
    found_user = get_user(new_user.username, session)

    if found_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username is already in use."
        )

    user: User = User(
        username=new_user.username, hashed_password=get_hash_password(new_user.password)
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return {"detail": "User was successfully created."}
