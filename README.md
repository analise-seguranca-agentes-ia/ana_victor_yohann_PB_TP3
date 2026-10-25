# TP3 - Projeto de Bloco: Análise e Segurança de Agentes de IA

## Objetivo
TP3 do Projeto de Bloco de Análise e Segurança de Agentes de IA, continuação do 
[TP2](https://github.com/analise-seguranca-agentes-ia/ana_victor_yohann_PB_TP2.git). 
Este TP consolida o projeto nas seguintes frentes:

- **Modelagem e classificação** implementação de um modelo para prever uma variável numérica derivada, avaliado por $R^2$, $RMSE$, análise por Residual Plot e Q-Q Plot, e formalização do problema de classificação de intenções;
- **Automação e CI/CD** desenvolvimento de uma suíte de testes com `pytest` e `TestClient` do FastAPI, configuração do pipeline automatizado com GitHub Actions para executar a suíte de testes;
- **Auditoria ZAP e Planejamento** varredura e correção de falhas de segurança com o OWASP ZAP e elaboração do planejamento do modelo e teste adversarial (`others/planejamento_tp3.md`).

O objetivo é evoluir a inteligência do sistema e garantir a robustez e automação da API, preparando a infraestrutura para o treinamento do modelo de classificação e o teste adversarial das próximas entregas.

## Equipe
- Ana Beatriz Rangel Mattos
- Victor Henrique Watanabe
- Yohann Matheus Gusso Guedes

## Dataset
**Customer Support Ticket Dataset**, disponível no Kaggle:
https://www.kaggle.com/datasets/suraj520/customer-support-ticket-dataset/data

O arquivo já está versionado neste repositório em `data/customer_support_tickets.csv`.
A fonte, as principais características, o dicionário de dados (significado de 
cada coluna) e o motivo da escolha do dataset estão documentados no início do 
notebook [eda/eda.ipynb](eda/eda.ipynb).

## Estrutura de pastas
```
TP2/
├── data/                        # dataset original
│   └── customer_support_tickets.csv
├── eda/
│   ├── eda.ipynb                # EDA completo, hipóteses e testes estatísticos
│   └── requirements.txt
├── fastapi/
│   ├── main.py                  # ponto de entrada + middlewares (headers, CORS, SlowAPI)
│   ├── database.py              # engine e sessão SQLModel
│   ├── sqlite_database.py       # criação e população inicial do banco (sqlite3)
│   ├── database.db              # banco SQLite com usuários e predictions de exemplo
│   ├── limiter.py               # instância do rate limiter (SlowAPI)
│   ├── requirements.txt
│   ├── models/                  # tabelas SQLModel e modelos Pydantic (extra='forbid')
│   ├── routes/                  # endpoints (auth, docs, health, prediction, user)
│   └── security/                # JWT + OAuth2PasswordBearer e RBAC
├── tests/
│   ├── conftest.py              # banco temporário e fixtures de autenticação
│   └── test_security.py         # testes dos controles de segurança
├── zap/
│   ├── zap_plan.yaml            # plano de automação do scan passivo
│   ├── zap_report_inicial.html  # relatório do scan antes das correções (+ .json)
│   ├── zap_report.html          # relatório do scan final, após as correções (+ .json)
│   └── scan_passivo_zap.md      # análise dos findings Medium e High
├── others/
│   ├── dfd.png                  # DFD com trust boundaries e tríade CIA
│   └── dfd-cia.md               # descrição do DFD e análise CIA
└── README.md
```

## Pré-requisitos
- Python 3.10 ou superior (o código utiliza unions do tipo `str | None`)
- `pip`
- [Docker](https://www.docker.com/) (apenas para reproduzir o scan do OWASP ZAP)

Opcionalmente, crie um ambiente virtual antes de instalar as dependências:

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/macOS
```

## EDA - Instruções

### Dependências

Para instalar as dependências do notebook, execute:

```bash
cd eda
pip install -r requirements.txt
```

### Pacotes Utilizados

- pandas: Leitura e manipulação do dataset;
- numpy: Operações numéricas;
- matplotlib: Geração dos gráficos;
- seaborn: Visualizações estatísticas;
- scipy: Testes de hipótese (t-test / Mann-Whitney);
- jupyter: Execução do notebook.

### Etapas do EDA

O notebook começa pela documentação do dataset (fonte, características, 
dicionário de dados e motivo da escolha) e segue as etapas do enunciado:

1. Compreensão do problema e do dataset
2. Inspeção inicial
3. Verificação da qualidade dos dados
4. Limpeza e preparação dos dados
5. Análise univariada
6. Análise multivariada, incluindo as hipóteses e os testes formais 
   (Mann-Whitney / t-test de Welch)
7. Identificação de outliers e anomalias
8. Documentação do EDA e conclusões

O notebook já está versionado com as saídas, então dá para ler os resultados 
sem executá-lo.


### Execução

Inicie o Jupyter com:

```bash
cd eda
jupyter notebook eda.ipynb
```

Ou, se preferir, abra o arquivo `eda/eda.ipynb` diretamente no VS Code (com as 
extensões *Python* e *Jupyter* instaladas) e execute as células por lá.

Em ambos os casos o notebook roda a partir do diretório `eda/`, o que é 
necessário porque ele lê o dataset pelo caminho relativo 
`../data/customer_support_tickets.csv`.

## FastAPI - Instruções

### Dependências

Para instalar as dependências necessárias, execute:

```bash
cd fastapi
pip install -r requirements.txt
```

### Pacotes Utilizados

- fastapi[standard]: Framework web;
- uvicorn: Servidor para execução da API;
- pydantic: Validação e tipagem de dados;
- sqlmodel: ORM para modelos e consultas ao banco SQLite;
- pyjwt: Geração e verificação de tokens;
- pwdlib[argon2]: Hashing de senhas;
- slowapi: Rate limiting;
- email-validator: Validação de e-mails nos modelos.

### Banco de dados (SQLite)

O banco `fastapi/database.db` possui duas tabelas:

| Tabela | Descrição |
|---|---|
| `user` | Usuários da API (id, username, roles, e-mail, nome e hash da senha) |
| `prediction` | Predições de intenção, cada uma com um `owner_id` (FK para `user.user_id`) que identifica seu proprietário |

A criação e a população inicial são feitas pelo script 
[fastapi/sqlite_database.py](fastapi/sqlite_database.py), utilizando `sqlite3`. 
O seed cria dois usuários (`johndoe` e `janedoe`) e uma prediction para cada um, 
o que permite demonstrar o controle de acesso por ownership.

O banco é criado e populado **automaticamente** ao iniciar a API, pois o 
`database.py` chama `init_and_seed_db()` na inicialização. O caminho do banco é 
resolvido a partir da pasta do código, então ele sempre é criado em 
`fastapi/database.db`, independentemente do diretório de onde a API ou os testes 
são executados. Para criá-lo manualmente, execute:

```bash
cd fastapi
python -c "from sqlite_database import init_and_seed_db; init_and_seed_db()"
```

O seed só insere dados se a tabela `user` estiver vazia, então executar o script 
mais de uma vez não duplica registros. Para recriar o banco do zero, apague o 
arquivo `fastapi/database.db` e execute o comando acima novamente.

O `sqlite3` é usado apenas na criação/população inicial. Todas as consultas 
realizadas pela API utilizam **SQLModel**, sem SQL raw.

### Execução

A partir do diretório `fastapi/`, inicie o servidor com um dos dois comandos:

```bash
python main.py
```

ou

```bash
uvicorn main:app --reload
```

Também é possível iniciar a partir da raiz do projeto:

```bash
python fastapi/main.py
```

ou

```bash
uvicorn main:app --app-dir fastapi --reload
```

A pasta da aplicação se chama `fastapi`, o mesmo nome da biblioteca, então ela 
não pode virar um pacote Python (um `fastapi/__init__.py` esconderia o framework). 
Por isso o `main.py` adiciona a própria pasta ao `sys.path`, o que faz os imports 
internos funcionarem independentemente do diretório de onde a API é executada.

No Linux/macOS, use `python3` caso `python` não esteja disponível.

- **API URL:** `http://127.0.0.1:8000`
- **Documentação Swagger:** `http://127.0.0.1:8000/docs`

### Rotas

| Método | Rota | Protegida | Descrição |
|---|---|---|---|
| `GET` | `/health` | Não | Verifica se a API está ativa |
| `POST` | `/auth/token` | Não | Autentica o usuário (form-urlencoded) e retorna o token JWT. Limitada a **10 requisições/minuto** por cliente |
| `POST` | `/auth/register` | Não | Cadastra um novo usuário com `{"username", "password"}` |
| `GET` | `/users` | Sim (admin) | Lista os usuários cadastrados |
| `POST` | `/predictions/predict` | Sim (Bearer) | Recebe `{"text": "..."}`, salva a prediction com o usuário autenticado como proprietário e retorna `201` |
| `GET` | `/predictions` | Sim (Bearer) | Lista apenas as predictions do usuário autenticado |
| `GET` | `/predictions/{id}` | Sim (Bearer) | Retorna a prediction pelo ID somente se ela pertencer ao usuário autenticado (`403` caso pertença a outro usuário, `404` caso não exista) |

Nas rotas protegidas, o token só é aceito se tiver assinatura válida, as claims 
`sub` e `exp` e se o `sub` corresponder a um usuário cadastrado no banco. Depois 
disso, o RBAC confere se a role do usuário tem permissão para a rota.

### Controles de segurança

| Controle | Implementação |
|---|---|
| Autenticação | JWT HS256 com expiração de 30 minutos e senhas em hash Argon2 ([security/auth.py](fastapi/security/auth.py)) |
| Autorização | RBAC por role ([security/rbac.py](fastapi/security/rbac.py)) e controle por ownership contra BOLA ([routes/prediction.py](fastapi/routes/prediction.py)) |
| Validação de entrada | Modelos Pydantic com `extra='forbid'` ([models/](fastapi/models/)) |
| Banco de dados | Consultas com SQLModel, sem SQL raw |
| Headers HTTP | HSTS, X-Frame-Options, X-Content-Type-Options e Content-Security-Policy via middleware ([main.py](fastapi/main.py)) |
| CORS | Allowlist explícita de origens: `http://localhost:3000` e `http://localhost:8080` ([main.py](fastapi/main.py)) |
| Rate limiting | SlowAPI com 10 requisições/minuto por cliente em `/auth/token` ([routes/auth.py](fastapi/routes/auth.py)) |
| Documentação | Swagger servido com versão fixa, SRI e sem script inline, compatível com o CSP ([routes/docs.py](fastapi/routes/docs.py)) |

#### Autenticação

Para testar as rotas protegidas, autentique-se via `/auth/token` ou use o botão `Authorize` no Swagger com um dos seguintes usuários:

##### Usuário admin:

Username: `johndoe`
Password: `johndoe123`

##### Usuário normal

Username: `janedoe`
Password: `janedoe123`

## Testes - Instruções

### Dependências

O `pytest` já está incluído no `fastapi/requirements.txt`. Caso ainda não tenha 
instalado as dependências da API, execute:

```bash
cd fastapi
pip install -r requirements.txt
```

### Execução

A partir da **raiz do projeto**, execute:

```bash
python -m pytest tests -v
```

O arquivo [tests/conftest.py](tests/conftest.py) adiciona o diretório `fastapi/` 
ao `sys.path` e direciona a aplicação para um **banco temporário**, criado e 
populado com o mesmo seed (`johndoe` e `janedoe`) a cada execução e removido ao 
final. Assim, os testes sempre partem do mesmo estado e não alteram o 
`fastapi/database.db` versionado.

Os tokens JWT são gerados uma única vez por execução, para não consumir o 
limite de 10 requisições/minuto do `/auth/token`.

### Cenários cobertos

Os testes estão em [tests/test_security.py](tests/test_security.py):

| Teste | Cenário | Resultado esperado |
|---|---|---|
| `test_access_without_token` | Acesso a `GET /predictions` sem token JWT | `401 Unauthorized` |
| `test_reject_token_for_unknown_user` | Token com assinatura válida, mas com `sub` de um usuário que não existe no banco | `401 Unauthorized` |
| `test_reject_token_without_exp` | Token de um usuário válido, mas sem a claim `exp` | `401 Unauthorized` |
| `test_access_other_user_resource_bola` | `johndoe` cria uma prediction e `janedoe` tenta acessá-la pelo ID (BOLA) | `403 Forbidden` |
| `test_reject_extra_fields_in_request_body` | Envio do campo extra `role` no body de `POST /predictions/predict` | `422 Unprocessable Entity` com erro do tipo `extra_forbidden` no campo `role` |
| `test_rate_limit_on_auth_token` | 11 tentativas de login com senha errada em sequência (simulação de brute force) | `401` nas 10 primeiras e `429 Too Many Requests` na 11ª |

## OWASP ZAP - Scan passivo

A API foi auditada com um scan **passivo** do OWASP ZAP, executado via Docker com 
o plano de automação [zap/zap_plan.yaml](zap/zap_plan.yaml). O plano importa o 
`/openapi.json`, requisita a página `/docs` e as rotas protegidas e exporta os 
relatórios, sem nenhum job de scan ativo.

Para reproduzir (Git Bash, a partir da raiz do projeto), suba a API aceitando 
conexões do container:

```bash
uvicorn main:app --app-dir fastapi --host 0.0.0.0 --port 8000
```

Em outro terminal, gere um token e execute o ZAP. O token é enviado em todas as 
requisições, para que o ZAP também analise as respostas das rotas protegidas:

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/token -d "username=janedoe&password=janedoe123" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

docker run --rm \
  -e ZAP_AUTH_HEADER_VALUE="Bearer $TOKEN" \
  -e ZAP_AUTH_HEADER_SITE="host.docker.internal" \
  -v "$(pwd -W)/zap:/zap/wrk:rw" \
  ghcr.io/zaproxy/zaproxy:stable zap.sh -cmd -autorun /zap/wrk/zap_plan.yaml
```

Os relatórios são gerados em `zap/zap_report.html` e `zap/zap_report.json`. O 
scan cria registros de exemplo no banco, então restaure-o depois com 
`git restore fastapi/database.db`.

O primeiro scan encontrou dois findings **Medium** (CSP ausente e SRI ausente 
no Swagger), que foram corrigidos. O scan final não tem findings Medium nem High. 
A análise completa de cada finding (severidade, confiança, URL afetada, correção e 
validação) está em [zap/scan_passivo_zap.md](zap/scan_passivo_zap.md).

## DFD e Tríade CIA

O DFD da API do TP2, com entradas, saídas, trust boundaries e a classificação 
CIA de cada componente indicada no próprio diagrama, está em 
[others/dfd.png](others/dfd.png).

A descrição dos componentes, dos fluxos, das trust boundaries, a justificativa 
da classificação CIA, as fragilidades e os controles implementados estão em 
[others/dfd-cia.md](others/dfd-cia.md).

