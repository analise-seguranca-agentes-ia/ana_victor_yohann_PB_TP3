import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlmodel import Field, SQLModel


class Prediction(SQLModel, table=True):
    prediction_id: uuid.UUID = Field(
        default_factory=uuid.uuid4, unique=True, primary_key=True
    )
    owner_id: uuid.UUID = Field(foreign_key="user.user_id", ondelete="CASCADE")
    text: str
    intention: str
    created_at: datetime


class PostPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = PydanticField(
        description="Texto do ticket escrito pelo cliente.",
        examples=["I want to cancel my order and get my money back."],
    )


class GetPredictionResponse(BaseModel):
    prediction_id: uuid.UUID = PydanticField(description="Id (UUID) da prediction.")
    text: str = PydanticField(description="Texto enviado para classificação.")
    intention: str = PydanticField(description="Intenção prevista para o texto.")
