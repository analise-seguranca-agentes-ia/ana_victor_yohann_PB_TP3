from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    access_token: str = Field(description="Token JWT a ser enviado no header Authorization.")
    token_type: str = Field(description="Tipo do token. Sempre 'bearer'.", examples=["bearer"])


class TokenData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str | None = None
