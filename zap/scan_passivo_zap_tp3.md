# Auditoria final com OWASP ZAP (TP3)

## Objetivo

No TP3 a auditoria com o OWASP ZAP passou a exigir a correção de todos os findings de severidade Medium e High, sem a possibilidade de apenas justificar o risco. Este documento registra o scan passivo final da API, os findings encontrados, as correções realizadas e a evidência de que nenhum finding Medium ou High permanece. A API auditada é a mesma que será atacada por outra equipe no TP4.

## Como o scan foi executado

O scan foi feito com o OWASP ZAP 2.17.0 rodando em Docker (imagem `ghcr.io/zaproxy/zaproxy:stable`), em modo somente passivo, sem nenhum job de active scan. A API foi executada localmente com o código final do TP3, e o ZAP acessou a API pelo endereço `http://host.docker.internal:8000`.

O plano de automação está em [zap_plan.yaml](zap_plan.yaml). Ele importa a especificação OpenAPI, o que faz o ZAP requisitar todas as rotas documentadas, requisita explicitamente a página `/docs` e as rotas protegidas e aguarda o fim da análise passiva antes de gerar os relatórios. Em relação ao TP2, o plano passou a incluir a rota `/users`, exclusiva de administradores, para que a resposta 403 por falta de perfil também fosse analisada.

As requisições foram feitas com o token JWT da usuária `janedoe`, enviado pelas variáveis `ZAP_AUTH_HEADER_VALUE` e `ZAP_AUTH_HEADER_SITE`. Assim o ZAP analisou também as respostas reais das rotas protegidas (200, 201, 403 e 422), e não apenas as respostas 401.

O comando abaixo foi executado no Git Bash, a partir da raiz do projeto e com a API rodando.

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/token -d "username=janedoe&password=janedoe123" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

MSYS_NO_PATHCONV=1 docker run --rm \
  -e ZAP_AUTH_HEADER_VALUE="Bearer $TOKEN" \
  -e ZAP_AUTH_HEADER_SITE="host.docker.internal" \
  -v "$(pwd -W)/zap:/zap/wrk:rw" \
  ghcr.io/zaproxy/zaproxy:stable zap.sh -cmd -autorun /zap/wrk/zap_plan.yaml
```

A importação do OpenAPI chama `POST /auth/register` e `POST /predictions/predict` com dados de exemplo e grava registros no banco. Por isso, depois do scan, o arquivo `fastapi/database.db` foi restaurado com `git restore fastapi/database.db`.

## Resultado

Os relatórios do scan final estão em [zap_report_tp3.html](zap_report_tp3.html) e [zap_report_tp3.json](zap_report_tp3.json). Os relatórios do TP2 foram mantidos na pasta como histórico.

**O scan final não encontrou nenhum finding de severidade High nem Medium.** Foram encontrados apenas dois findings de severidade Informational, descritos mais abaixo.

Os findings Medium que existiam na primeira versão da API, encontrados no scan inicial do TP2 ([zap_report_inicial.html](zap_report_inicial.html)), foram corrigidos e continuam ausentes no scan final.

**Content Security Policy (CSP) Header Not Set**, severidade Medium. Uma ocorrência no scan inicial do TP2, nenhuma no scan final do TP3.

**Sub Resource Integrity Attribute Missing**, severidade Medium. Duas ocorrências no scan inicial do TP2, nenhuma no scan final do TP3.

**Cross Domain JavaScript Source File Inclusion**, severidade Low. Uma ocorrência no scan inicial do TP2, nenhuma no scan final do TP3, porque foi resolvido junto com o finding de SRI.

Todos esses findings estavam na página `/docs` (Swagger UI), que é a única resposta HTML da API. As rotas da API em si, que respondem JSON, não geraram nenhum alerta Medium ou High.

## Findings Medium corrigidos

### Finding 1. Content Security Policy (CSP) Header Not Set

**Severidade.** Medium, com confiança High (plugin 10038, CWE 693, WASC 15).

**Onde foi detectado.** Na resposta HTML de `GET /docs`. Na verdade, nenhuma resposta da API enviava o header `Content-Security-Policy`, mas o ZAP aplica essa regra apenas a respostas HTML.

**Risco.** Sem CSP, o navegador executa qualquer script presente na página, venha de onde vier. Se alguém conseguir injetar conteúdo na página do Swagger (XSS), o script injetado roda com acesso ao token JWT que o usuário informou no botão Authorize.

**Correção.** O middleware `security_headers` passou a enviar o header em todas as respostas, com duas políticas. As rotas da API recebem uma política que bloqueia qualquer conteúdo, porque só devolvem JSON. O `/docs` recebe uma política que libera apenas os arquivos do Swagger UI na versão fixa do CDN, o script de inicialização da própria API e a busca do `/openapi.json`. A página padrão do FastAPI usava um script inline, o que obrigaria a liberar `'unsafe-inline'` na política, então o `/docs` passou a ser servido por `routes/docs.py`, com o script de inicialização em um arquivo próprio (`/docs/swagger-init.js`). O `/redoc`, que não era usado, foi desativado.

**Onde está no código.** Em `fastapi/main.py`, nas constantes `API_CSP` e `DOCS_CSP`, na criação do `FastAPI` com `docs_url=None` e `redoc_url=None` e no middleware `security_headers`. Em `fastapi/routes/docs.py`, na página do Swagger servida pela aplicação. Os trechos estão marcados com comentários `Correção ZAP` que indicam o finding corrigido.

**Evidência.** O finding não aparece no scan final do TP3 ([zap_report_tp3.html](zap_report_tp3.html)). Também não apareceu nenhum alerta sobre a própria política, como uso de `unsafe-inline` ou diretivas faltando.

### Finding 2. Sub Resource Integrity Attribute Missing

**Severidade.** Medium, com confiança High (plugin 90003, CWE 345, WASC 15).

**Onde foi detectado.** Em `GET /docs`, com duas ocorrências. O CSS e o JavaScript do Swagger UI eram carregados do CDN jsDelivr sem o atributo `integrity` e com a versão `@5`, que aponta sempre para a versão 5 mais recente, de modo que o arquivo entregue podia mudar a qualquer momento.

**Risco.** Sem SRI, o navegador não tem como verificar se o arquivo recebido é o esperado. Se o CDN ou o pacote no npm forem comprometidos, um JavaScript malicioso seria executado dentro da página de documentação da API, com acesso ao token JWT do usuário.

**Correção.** A versão do Swagger UI foi fixada em 5.33.1, e os dois arquivos passaram a ter o atributo `integrity` com o hash SHA 384 de cada arquivo, junto com `crossorigin="anonymous"`. Os hashes foram calculados a partir dos arquivos baixados do próprio CDN. O CSP do `/docs` só permite scripts e estilos desse caminho do CDN, na versão fixa.

**Onde está no código.** Em `fastapi/routes/docs.py`, nas constantes `SWAGGER_UI_VERSION`, `SWAGGER_JS_SRI` e `SWAGGER_CSS_SRI` e no HTML da página, e em `fastapi/main.py`, na constante `DOCS_CSP`. Os trechos estão marcados com comentários `Correção ZAP` que indicam o finding corrigido.

**Evidência.** O finding não aparece no scan final do TP3. O alerta Low de inclusão de JavaScript de outro domínio também deixou de aparecer, porque o ZAP considera mitigado um script externo com SRI. No navegador, o Swagger carrega normalmente, o que mostra que os hashes conferem, já que o navegador bloquearia os arquivos se não conferissem.

**Risco residual.** O `/docs` continua dependendo da disponibilidade do jsDelivr. Se o CDN estiver fora do ar, a documentação não carrega, mas a API continua funcionando normalmente.

## Findings Low e Informational do scan final

**Authentication Request Identified (Informational).** O ZAP apenas identificou que `POST /auth/token` é a requisição de login, com os campos `username` e `password`. Não é uma vulnerabilidade. Esse endpoint tem rate limiting de 10 requisições por minuto por cliente.

**Modern Web Application (Informational).** Indica que o `/docs` é uma aplicação JavaScript (Swagger UI). Também não é uma vulnerabilidade.


## Documentação da API no Swagger

Como parte da auditoria final, a documentação em `/docs` foi completada para que a outra equipe consiga entender a superfície da API no TP4. A aplicação passou a ter título, descrição e versão, com uma explicação de como obter e usar o token JWT e do limite do `/auth/token`. Cada rota recebeu um resumo e uma descrição, os parâmetros e os campos dos modelos receberam descrição e exemplo, e todas as respostas de erro que cada rota pode retornar (401, 403, 404, 409, 422 e 429) foram documentadas com um exemplo do corpo. O esquema de autenticação OAuth2 com token Bearer também ganhou descrição, e o botão Authorize do Swagger permite testar as rotas protegidas.

## Limitações

O scan foi feito em HTTP local, sem TLS. O header HSTS é enviado, mas só tem efeito quando a API é servida por HTTPS, como acontece pela URL pública do Cloudflare Tunnel.

Por ser passivo, o scan não testa ataques como injeção ou BOLA. Ele apenas analisa as requisições e respostas. Esses controles são cobertos pelos testes automatizados em `tests/` e serão alvo do pentest previsto para o TP4.
