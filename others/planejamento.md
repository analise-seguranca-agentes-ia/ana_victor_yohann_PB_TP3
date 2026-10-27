# Planejamento da fase preditiva (TP3)

Este documento registra as decisões tomadas no TP3 para a fase preditiva do projeto, que começa no TP4. Ele define o algoritmo de classificação candidato, a forma de representar o texto do cliente e o endereço público da API que será usado como alvo autorizado no pentest dos próximos TPs.

## 1. Problema de classificação

Conforme formalizado na seção 3 do notebook [eda_tp3.ipynb](../eda/eda_tp3.ipynb), o modelo deve responder à pergunta "dado o texto que o cliente escreveu ao abrir o ticket, qual é o tipo da sua solicitação?".

A entrada é a coluna `Ticket Description`, já limpa na etapa 1.4 do notebook. O alvo é a coluna `Ticket Type`, uma variável categórica nominal com cinco classes (`Refund request`, `Technical issue`, `Cancellation request`, `Product inquiry` e `Billing inquiry`). As classes são balanceadas, com frequências entre 19,29% e 20,69%, então um modelo que sempre previsse a classe mais frequente acertaria 20,69% dos casos. Esse valor é a linha de base que qualquer modelo útil precisa superar.

## 2. Algoritmo de classificação candidato

### Escolha

O algoritmo candidato é a **regressão logística multiclasse** (`LogisticRegression` do `scikit-learn`).

### Por que a regressão logística

**É adequada para texto vetorizado.** Depois da vetorização, cada descrição vira uma linha de uma matriz com milhares de colunas e quase todos os valores iguais a zero. Modelos lineares como a regressão logística lidam bem com esse formato, treinam rapidamente e são o ponto de partida usual para classificação de texto.

**Fornece probabilidades.** Além da classe prevista, a regressão logística retorna a probabilidade de cada classe (`predict_proba`). Isso permite avaliar o modelo com curvas ROC e AUC por classe, como visto em aula, e permite que a API use um limiar de confiança, respondendo que a intenção é indefinida quando nenhuma classe tiver probabilidade suficiente, em vez de devolver um palpite.

**É interpretável.** O modelo aprende um peso para cada palavra em cada classe. Com esses pesos é possível explicar por que um texto foi classificado de determinada forma e verificar se o modelo está usando palavras que fazem sentido para cada intenção. Do ponto de vista de segurança, os pesos também mostram quais palavras mais influenciam a decisão, o que ajuda a entender como um atacante poderia manipular o texto para forçar uma classe, um dos cenários a investigar no pentest do TP4.

**Tem poucos hiperparâmetros.** Os principais são a regularização `C` e o `class_weight`. Eles serão escolhidos com `GridSearchCV`, usando validação cruzada estratificada com 5 partições, como visto em aula. Como as classes são balanceadas, o ajuste de pesos por classe provavelmente não fará diferença, mas será incluído na busca para confirmar.

**É leve.** O modelo treinado é pequeno, é salvo com `joblib` e faz a previsão em poucos milissegundos. Isso é importante para a disponibilidade da API, que precisa responder rapidamente mesmo sob carga.

### Alternativas que serão comparadas

O **SVM linear** (`LinearSVC`) costuma ter desempenho parecido ou um pouco melhor em classificação de texto, mas não fornece probabilidades diretamente, o que dificulta a curva ROC e o limiar de confiança. O **Naive Bayes multinomial** (`MultinomialNB`) é um modelo simples e muito rápido, pensado para contagens de palavras, e serve como comparação. Os três algoritmos serão avaliados no TP4 com a mesma validação cruzada. A regressão logística só será mantida se o seu desempenho for equivalente ao do melhor deles.

### Métricas de avaliação

Como as classes são balanceadas, a **acurácia** será a métrica principal, sempre comparada com a linha de base de 20,69%. Ela será complementada pela matriz de confusão, pela precisão, recall e F1 de cada classe e pela curva ROC com AUC de cada classe contra as demais.

## 3. Representação do texto com CountVectorizer

### Por que o CountVectorizer

O modelo só trabalha com números, então o texto precisa ser convertido antes do treino. O `CountVectorizer` transforma cada descrição em um vetor em que cada posição corresponde a uma palavra do vocabulário e o valor é o número de vezes que essa palavra aparece no texto.

Essa representação foi escolhida porque é simples, não depende de modelos externos e é interpretável, já que cada coluna da matriz é uma palavra conhecida. Isso se combina com a interpretabilidade da regressão logística, porque cada peso aprendido pelo modelo corresponde a uma palavra. Também é a representação usada em aula para a análise multivariada de texto (qui quadrado entre palavras e alvo) e para o modelo persistido com `joblib`.

### Configuração inicial

O vetorizador será usado com `stop_words="english"`, porque as descrições estão em inglês e palavras muito comuns, como artigos e preposições, não ajudam a diferenciar as intenções. Os demais parâmetros começam com os valores padrão. O uso de pares de palavras (`ngram_range`) e a frequência mínima de cada termo (`min_df`) serão avaliados no TP4 junto com a busca de hiperparâmetros.

Com essa configuração, aplicada às descrições limpas, o vocabulário tem 6.737 termos e cada descrição tem em média 21 termos diferentes. Cerca de 99,7% dos valores da matriz são zero, por isso ela é armazenada em formato esparso.

### Treino e uso na API

No treino, o vocabulário é aprendido com `fit_transform` apenas sobre os dados de treino. Na API, os textos novos passam somente por `transform`, que mantém o vocabulário fixo e ignora palavras que não existiam no treino. O vetorizador e o modelo serão salvos juntos com `joblib` e carregados uma única vez, quando a API iniciar, e não a cada requisição.

### Cuidados

As frases fixas dos templates, como o pedido de ajuda e a menção às etapas do manual, aparecem em praticamente todos os tickets (etapa 1.5 do notebook) e não são removidas pelas stop words. O esperado é que o modelo atribua pouco peso a elas, o que será verificado nos coeficientes. Os nomes de produtos, inseridos nas descrições durante a limpeza, também viram palavras do vocabulário, mas não têm relação com a intenção do cliente.

Do ponto de vista de segurança, o texto enviado para `POST /predictions/predict` é a principal superfície de ataque do modelo, e o custo de vetorização cresce com o tamanho do texto. Por isso está planejado limitar o tamanho máximo do campo `text` no modelo Pydantic de entrada, para evitar negação de serviço com textos muito grandes.

## 4. Risco identificado

O EDA já indicava que as descrições foram geradas a partir de templates genéricos e que o `Ticket Type` é independente das demais variáveis (etapa 1.8 do notebook). Para medir esse risco antes do TP4, foi feito um teste preliminar, registrado na seção 3 do notebook, com o `CountVectorizer` e os três algoritmos candidatos em validação cruzada estratificada com 5 partições.

A regressão logística obteve acurácia média de 19,92%, o SVM linear 19,79% e o Naive Bayes multinomial 19,51%. Os três resultados ficaram abaixo da linha de base de 20,69%, ou seja, nenhum modelo foi melhor que sempre prever a classe mais frequente. **Com os dados atuais, o texto da descrição não separa as intenções do cliente.**

No início do TP4 esse resultado será confirmado com a busca de hiperparâmetros. Se ele se mantiver, há duas alternativas. A primeira é complementar o dataset com exemplos de texto em que a mensagem e a intenção tenham relação real, como o dataset Bitext de atendimento ao cliente usado em aula. A segunda é manter o modelo treinado apenas para dar funcionalidade real à rota `/predictions/predict`, já que o foco da disciplina é a segurança da API, documentando que o desempenho está no nível do acaso. A decisão será tomada pelo grupo no início do TP4.

## 5. URL pública da API

### Endereço

A URL pública da API, alvo autorizado para o pentest dos TP4 e TP5, é

**`https://rated-intend-shows-singles.trycloudflare.com`**

A documentação interativa fica no mesmo endereço, no caminho `/docs`.

### Como a URL foi gerada

A API foi exposta com o Cloudflare Tunnel no modo de túnel rápido, que cria uma URL HTTPS pública sem abrir portas no roteador, sem hospedagem e sem conta na Cloudflare. A URL foi gerada em 26/10/2026 com a API e o túnel rodando em dois terminais, a partir da raiz do projeto.

```bash
uvicorn main:app --app-dir fastapi --host 0.0.0.0 --port 8000
cloudflared tunnel --url http://localhost:8000
```

### Limitações e escopo

O túnel rápido gera um endereço novo a cada execução e só funciona enquanto a API e o túnel estão rodando. Antes do início do TP4 a API será executada novamente, e o endereço atualizado será registrado neste documento e informado à equipe responsável pelo ataque.

O escopo autorizado do pentest é somente a API acessível por essa URL. Ficam fora do escopo a máquina que executa a API, o serviço da Cloudflare e qualquer outro endereço.