from datetime import datetime, timedelta, timezone

import jwt
from database import get_session
from jwt.exceptions import InvalidTokenError
from models.auth import TokenData
from models.user import PostUserLoginRequest, User
from pwdlib import PasswordHash
from sqlmodel import Session, select

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = "afbf8e8c498a091441ed002a0435a16c069b0aec2049e4a518d045f51ee82f85"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

ADMIN_USERNAME = "admin-v01"
ADMIN_EMAIL = "admin.v01@example.com"
ADMIN_FULL_NAME = "Administrator V01"
ADMIN_PASSWORD = "dumbpassword"

password_hash = PasswordHash.recommended()

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate user credentials.",
    headers={"WWW-Authenticate": "Bearer"},
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/token",
    description="Token JWT obtido em POST /auth/token. Enviado no header Authorization: Bearer <token>.",
)


def verify_password(input_password: str, hashed_password: str) -> bool:
    return password_hash.verify(input_password, hashed_password)


def get_hash_password(password: str) -> str:
    return password_hash.hash(password)


def get_user(username: str, session: Session) -> User | None:
    return session.exec(select(User).where(User.username == username)).first()


def authenticate_user(login: PostUserLoginRequest, session: Session) -> User:
    found_user = get_user(login.username, session)

    if not found_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User could not be found."
        )

    if not verify_password(login.password, found_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials."
        )

    return found_user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


async def verify_access_token(
    token: str = Depends(oauth2_scheme),
) -> TokenData:

    try:
        # Tokens sem "sub" ou sem "exp" são rejeitados já na decodificação.
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp"]},
        )

        username = payload.get("sub")

        if not username:
            raise credentials_exception

        token_data = TokenData(username=username)

        return token_data
    except InvalidTokenError:
        raise credentials_exception


async def get_current_user(
    token_data: TokenData = Depends(verify_access_token),
    session: Session = Depends(get_session),
):
    if not token_data.username:
        raise credentials_exception

    # A assinatura válida não basta: o "sub" do token precisa corresponder a um
    # usuário cadastrado no banco. Um token emitido para um usuário que não
    # existe (ou que foi removido) é recusado antes de chegar às rotas.
    # A permissão de cada rota é verificada em seguida pelo RoleChecker (rbac.py).
    user = get_user(token_data.username, session)

    if user is None:
        raise credentials_exception

    return user
