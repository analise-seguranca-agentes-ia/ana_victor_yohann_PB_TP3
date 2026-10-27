from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

# Correção ZAP (TP2, Finding 1 e Finding 2).
# Página do Swagger UI servida pela própria aplicação no lugar da página padrão
# do FastAPI, para atender aos findings do scan passivo do OWASP ZAP:
# - os arquivos do CDN têm versão fixa e hash de integridade (SRI), então o
#   navegador recusa o arquivo se ele for alterado no CDN;
# - o script de inicialização é servido como arquivo próprio (/docs/swagger-init.js),
#   sem script inline, o que permite um Content-Security-Policy sem 'unsafe-inline'.

SWAGGER_UI_VERSION = "5.33.1"
SWAGGER_UI_CDN = f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{SWAGGER_UI_VERSION}"

SWAGGER_JS_SRI = "sha384-ZPehFMQommnnuaZ4rpxgkgTT2DKFVp4hZC/7pLit+9Lek9T1YGSo23eHFbvNkXkw"
SWAGGER_CSS_SRI = "sha384-Ov4/wv3j2bmct8cDc5X4ngJZohVPzEmc6uDPH8WeljUxO5vtoykvMEfbu9Vh6RaW"

DOCS_HTML = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>API TP3 - Swagger UI</title>
<link rel="stylesheet" href="{SWAGGER_UI_CDN}/swagger-ui.css"
      integrity="{SWAGGER_CSS_SRI}" crossorigin="anonymous">
</head>
<body>
<div id="swagger-ui"></div>
<script src="{SWAGGER_UI_CDN}/swagger-ui-bundle.js"
        integrity="{SWAGGER_JS_SRI}" crossorigin="anonymous"></script>
<script src="/docs/swagger-init.js"></script>
</body>
</html>
"""

SWAGGER_INIT_JS = """window.ui = SwaggerUIBundle({
    url: "/openapi.json",
    dom_id: "#swagger-ui",
    layout: "BaseLayout",
    deepLinking: true,
    presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
});
"""

docs_router = APIRouter(include_in_schema=False)


@docs_router.get("/docs", response_class=HTMLResponse)
async def swagger_ui():
    return HTMLResponse(DOCS_HTML)


@docs_router.get("/docs/swagger-init.js")
async def swagger_init():
    return Response(SWAGGER_INIT_JS, media_type="application/javascript")
