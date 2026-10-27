from database import get_session
from models.user import GetUserResponse, User, UserRole
from routes.responses import RESPONSE_401, RESPONSE_403_ROLE
from security.rbac import RoleChecker
from sqlmodel import Session, select

from fastapi import APIRouter, Depends

user_router = APIRouter(prefix="/users", tags=["User"])

allow_read_users = RoleChecker([UserRole.ADMIN.name.lower()])


@user_router.get(
    "",
    dependencies=[Depends(allow_read_users)],
    response_model=list[GetUserResponse],
    summary="Lista os usuários cadastrados",
    description=(
        "Exige token JWT de um usuário com o perfil **admin**. "
        "Retorna username, e-mail e nome de cada usuário, sem o hash da senha."
    ),
    responses={**RESPONSE_401, **RESPONSE_403_ROLE},
)
async def get_users(
    session: Session = Depends(get_session),
):
    users = session.exec(select(User)).all()

    return users
