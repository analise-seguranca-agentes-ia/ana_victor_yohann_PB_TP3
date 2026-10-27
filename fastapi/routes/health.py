from fastapi import APIRouter

health_router = APIRouter(prefix="/health", tags=["health"])


@health_router.get(
    "",
    summary="Verifica se a API está no ar",
    description="Rota pública, sem autenticação. Retorna uma mensagem fixa quando a API está respondendo.",
    responses={200: {"content": {"application/json": {"example": {"details": "Conectado à API."}}}}},
)
async def check_health():
    return {"details": "Conectado à API."}
