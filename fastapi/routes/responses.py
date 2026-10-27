# Respostas de erro reutilizadas na documentação das rotas (Swagger em /docs).
# Cada rota lista apenas os códigos que ela pode de fato retornar.

RESPONSE_401 = {
    401: {
        "description": "Token ausente, inválido, expirado ou de um usuário que não existe.",
        "content": {"application/json": {"example": {"detail": "Could not validate user credentials."}}},
    }
}

RESPONSE_403_ROLE = {
    403: {
        "description": "O usuário autenticado não tem o perfil exigido pela rota.",
        "content": {"application/json": {"example": {"detail": "Access denied. You don't have permission to access this action."}}},
    }
}

RESPONSE_422 = {
    422: {
        "description": "Corpo ou parâmetro inválido, incluindo campos não previstos no modelo (extra='forbid').",
    }
}
