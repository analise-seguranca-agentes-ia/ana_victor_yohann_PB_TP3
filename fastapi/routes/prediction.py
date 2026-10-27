import uuid
from datetime import UTC, datetime
from random import choice

from database import get_session
from models.prediction import (GetPredictionResponse, PostPredictionRequest,
                               Prediction)
from models.user import User, UserRole
from routes.responses import RESPONSE_401, RESPONSE_403_ROLE, RESPONSE_422
from security.rbac import RoleChecker
from sqlmodel import Session, select

from fastapi import APIRouter, Depends, HTTPException, Path, status

prediction_router = APIRouter(prefix="/predictions", tags=["prediction"])


allow_create_prediction = RoleChecker(
    [UserRole.ADMIN.name.lower(), UserRole.DEFAULT.name.lower()]
)
allow_read_prediction = RoleChecker(
    [UserRole.ADMIN.name.lower(), UserRole.DEFAULT.name.lower()]
)

user_intentions = [
    "Refund request",
    "Software bug",
    "Network problem",
    "Account access",
]


@prediction_router.post(
    "/predict",
    response_model=GetPredictionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Classifica a intenção de um texto",
    description=(
        "Recebe o texto do ticket, retorna a intenção prevista e grava a prediction "
        "vinculada ao usuário autenticado (`owner_id`). Exige token JWT. "
        "Nesta etapa a intenção ainda é sorteada (modelo simulado). "
        "Campos além de `text` são rejeitados com 422."
    ),
    responses={**RESPONSE_401, **RESPONSE_403_ROLE, **RESPONSE_422},
)
async def predict_intention(
    text: PostPredictionRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(allow_create_prediction),
):
    user_intent = Prediction(
        owner_id=current_user.user_id,
        text=text.text,
        intention=choice(user_intentions),
        created_at=datetime.now(UTC),
    )

    session.add(user_intent)
    session.commit()
    session.refresh(user_intent)

    return user_intent


@prediction_router.get(
    "",
    response_model=list[GetPredictionResponse],
    summary="Lista as predictions do usuário autenticado",
    description=(
        "Exige token JWT. Retorna apenas as predictions cujo `owner_id` é o do "
        "usuário autenticado. Predictions de outros usuários nunca são listadas."
    ),
    responses={**RESPONSE_401, **RESPONSE_403_ROLE},
)
async def get_user_predictions(
    session: Session = Depends(get_session),
    current_user: User = Depends(allow_read_prediction),
):
    predictions = session.exec(
        select(Prediction).where(Prediction.owner_id == current_user.user_id)
    )

    return predictions


@prediction_router.get(
    "/{id}",
    response_model=GetPredictionResponse,
    summary="Consulta uma prediction pelo id",
    description=(
        "Exige token JWT. Retorna a prediction somente se ela pertencer ao usuário "
        "autenticado (controle de ownership contra BOLA)."
    ),
    responses={
        **RESPONSE_401,
        403: {
            "description": "A prediction pertence a outro usuário, ou o usuário não tem o perfil exigido.",
            "content": {"application/json": {"example": {"detail": "Access forbidden."}}},
        },
        404: {
            "description": "Nenhuma prediction com esse id.",
            "content": {"application/json": {"example": {"detail": "Could not find prediction"}}},
        },
        **RESPONSE_422,
    },
)
async def get_user_prediction_by_id(
    id: uuid.UUID = Path(description="Id (UUID) da prediction."),
    session: Session = Depends(get_session),
    current_user: User = Depends(allow_read_prediction),
):
    prediction = session.exec(
        select(Prediction).where(Prediction.prediction_id == id)
    ).first()

    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Could not find prediction"
        )

    if prediction.owner_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden."
        )

    return prediction
