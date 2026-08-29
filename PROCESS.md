## Contexto

O projeto chegou com a arquitetura principal pronta (modelagem de dados,
herança/polimorfismo em `Dispositivo`, autenticação com dois perfis,
painel de energia calculado a partir do histórico real). O próprio
`README.md` documentava três lacunas conhecidas: automações que não
disparavam sozinhas, envio de e-mail dependente de SMTP configurado, e
ausência de proteção CSRF.

## Rodada 1 — Agendador de automações

**Pedido:** fazer as automações (`Automacao`/`AutomacaoAcao`, já com CRUD
funcionando) disparar sozinhas de verdade, no horário configurado.

**Decisão de arquitetura:** um `BackgroundScheduler` do APScheduler,
rodando dentro do próprio processo Flask (`services/agendador.py`), em vez
de um serviço externo — mais simples de rodar e demonstrar num projeto
acadêmico, sem infraestrutura extra. O job roda a cada minuto e chama
`dispositivo.ligar()`/`desligar()` — o mesmo método que o botão da UI usa
— então o `RegistroUso` gerado (`usuario=None`, marcando que foi a
automação) entra no cálculo de energia normalmente, sem caminho especial.

**Detalhes que precisaram de atenção:**
- **Fuso horário.** O resto do sistema trabalha em UTC (`agora()` em
  `models.py`), mas o campo `horario` (`"HH:MM"`) da automação representa
  hora local de quem mora na casa. Adicionei `TIMEZONE` em `config.py`
  (padrão `America/Sao_Paulo`) e uso `zoneinfo` pra comparar.
- **Windows não tem banco de fusos horários embutido** — `zoneinfo` só
  funciona com o pacote `tzdata` instalado. Sem isso, `ZoneInfo("America/
  Sao_Paulo")` levanta `ZoneInfoNotFoundError` — foi adicionado no
  `requirements.txt`.
- **Reloader do Flask em modo debug sobe dois processos** (o observador e o
  worker). Sem cuidado, o agendador ligaria duas vezes e disparava cada
  automação duas vezes por minuto. Guardei a inicialização atrás de
  `WERKZEUG_RUN_MAIN`.

**Validação:** rodei o smoke test (24/24 OK) e um teste manual que cria uma
automação com o horário atual e chama a função interna do agendador
diretamente (sem esperar o minuto virar), confirmando que o dispositivo
liga de verdade e o `RegistroUso` fica com `usuario_id=None`.

## Rodada 2 — Seis melhorias para maximizar a nota

Depois de comparar o app com um protótipo visual (mockup) mais completo do
mesmo projeto, sugeri seis melhorias priorizadas por impacto vs. esforço,
todas aprovadas para implementação:

1. **Alerta inteligente de consumo** — a peça que mais materializa a
   categoria INTELLIGENCE do projeto. `services/energia.py::gerar_alerta()`
   compara o consumo de cada dispositivo com a semana anterior e aponta o
   que mais cresceu, acima de um limiar.
2. **Toggle de automação ativa/inativa** — nova rota `alternar_automacao`
   em `main.py`, respeitando a mesma permissão de controle do dispositivo.
3. **Comparação semanal + projeção mensal** — no painel de energia.
4. **Gráfico empilhado de consumo diário por cômodo** — usei um método de
   visualização de dados (via IAra) com paleta categórica validada
   contra daltonismo, ordem de cor fixa por cômodo nunca por posição,
   legenda, marcas com espaçamento consistente.
5. **Polimento de login/dashboard** — filtro por cômodo (chips + JS puro),
   botões "continuar como Admin/Comum" e "lembrar de mim".
6. **Proteção CSRF** — `Flask-WTF` em todos os 8 formulários POST do app.

### Bugs encontrados e corrigidos no processo

- **`NameError: timedelta`** em `services/agendador.py` — a função
  `proxima_automacao()` usava `timedelta` sem importar. Pego pelo
  `smoke_test.py` na primeira execução após a mudança, corrigido na hora.
- **Alerta de consumo absurdo (10794%).** O `seed.py` só gerava uma semana
  de histórico, então o período "semana anterior" usado como base de
  comparação ficava praticamente vazio — dividir por um número perto de
  zero explode a porcentagem. Corrigido em duas frentes: (a) o alerta
  passou a exigir uma base mínima de consumo no período anterior antes de
  calcular variação, e (b) o `seed.py` foi estendido para duas semanas de
  histórico, com o ar-condicionado tendo uma tendência real de alta
  (~21–31%) — assim o recurso fica demonstrável com um número plausível em
  vez de "sem dados" ou um outlier de dados incompletos.
- **Seed sem nenhuma automação.** O banco de exemplo nunca criava uma
  `Automacao`, então o banner "próxima automação" e o toggle não tinham o
  que mostrar numa instalação nova. Adicionadas 4 automações de exemplo
  (luz do quarto e luz externa, ligar/desligar).

### Validação

- `smoke_test.py`: 24/24 checks, com CSRF desativado só no cliente de
  teste (`WTF_CSRF_ENABLED = False`) — prática padrão do Flask-WTF, CSRF
  continua ativo em uso normal.
- Testes manuais via `curl` contra o servidor real rodando: login e login
  rápido, toggle de dispositivo e de automação, filtro por cômodo,
  alerta e gráfico do painel de energia — todos conferidos ponta a ponta,
  incluindo o fluxo de CSRF (sessão + token) e não só o "caminho feliz".

## Estruturas de dados — escolhas e por quê

O projeto não implementa estruturas de dados customizadas do zero (não
fazia sentido reinventar uma árvore ou uma hash table quando Python e o
SQLAlchemy já dão as ferramentas certas) — mas cada uso das estruturas
prontas foi uma escolha deliberada, não a primeira coisa que funcionou:

- **`dict` pra agregação/lookup por cômodo** (`cor_comodo`, `por_comodo`
  em `energia.py`, `services/energia.py::consumo_diario_por_comodo`).
  Alternativa seria uma lista de tuplas `(nome, valor)` e buscar com um
  loop toda vez que precisasse do valor de um cômodo específico — O(n) a
  cada acesso. Com `dict`, cada acesso por nome é O(1); como a mesma cor
  de cômodo é consultada várias vezes por página (uma vez por segmento do
  gráfico, uma vez por linha da lista), a diferença é real mesmo em
  escala pequena.
- **`set` pra checar dia da semana** (`_dia_bate()` em
  `services/agendador.py`): `dias_pedidos = {d.strip() for d in
  dias_semana.split(",")}` em vez de manter a lista separada por vírgula
  e checar com `in` numa lista. Isso roda a cada minuto pro job do
  agendador — `in` num `set` é O(1), `in` numa lista seria O(n) (n
  pequeno aqui, mas é o tipo de hábito que importa quando o volume cresce).
- **Ordenação delegada ao banco, não repetida em Python**
  (`RegistroUso.query....order_by(RegistroUso.timestamp)`): o SQLite já
  devolve os registros ordenados por timestamp usando índice/ordenação
  no próprio motor do banco; o código Python nunca precisa rodar um
  `sorted()` em cima do resultado. Evita pagar O(n log n) duas vezes
  (uma no banco, outra em memória) pela mesma coisa.
- **Lista de tuplas + `sort()` (Timsort, O(n log n)) pra ranquear consumo**
  (`resumo_consumo()`): dispositivos de uma casa são poucas dezenas, no
  máximo. Uma estrutura de prioridade (heap) traria complexidade extra de
  código sem ganho real nessa escala — ordenar uma vez por requisição é
  simples e suficiente. Justifica a escolha da estrutura mais simples
  quando o volume de dados não pede uma mais sofisticada, não só a mais
  sofisticada por padrão.
- **Single Table Inheritance em vez de uma tabela por tipo de
  dispositivo** (`models.py`): a alternativa (Class Table Inheritance,
  uma tabela por subclasse com `JOIN`) evitaria colunas nulas para
  atributos que só fazem sentido em alguns tipos (`atributos_extra`
  cobre isso via coluna JSON em vez de colunas fixas), mas custaria um
  `JOIN` a mais em toda consulta de dispositivo — trade-off consciente: 
  menos normalização, menos joins, mais simples de consultar um comodo
  inteiro de uma vez (que é a consulta mais frequente do sistema, tanto no
  dashboard quanto no calculo de energia).

## Rodada 3 — Maquete 3D interativa e integrada

**Pedido:** um diferencial visual pro projeto — inicialmente cogitamos 3D de
verdade, decidimos que o risco/esforço não compensava e fizemos uma planta
isométrica (2.5D) como mockup pra validar a ideia dos "gatilhos" (clicar num
ícone liga/desliga o dispositivo, com feedback visual). O mockup agradou, e
a partir de um protótipo 3D à parte (Three.js, tour de câmera automático
pela casa) que já existia, juntamos as duas coisas: a cena 3D de verdade +
os gatilhos clicáveis — e depois conectamos isso ao Flask de verdade.

**Decisão de arquitetura pra integração:**
- **Reaproveitar a rota de toggle existente** (`/dispositivo/<id>/alternar`)
  em vez de criar uma rota nova só pra maquete — a mesma checagem de
  permissão, o mesmo `RegistroUso`, sem duplicar lógica de negócio. A
  chamada via `fetch` usa o token CSRF pelo header `X-CSRFToken` (o
  Flask-WTF já aceita isso por padrão, `WTF_CSRF_HEADERS`), então não
  precisou mudar a rota nem desligar proteção nenhuma pra AJAX funcionar.
- **Mapeamento por nome, não por tipo genérico.** A cena 3D é uma casa
  específica desenhada à mão (não gerada a partir de uma lista arbitrária
  de dispositivos), então o `casa3d.js` mapeia por nome exato ("Luz da
  Sala" → objeto 3D da luz da sala). Só 10 dos 13 dispositivos do seed têm
  um objeto correspondente na cena — os outros três (Câmera da Sala,
  Geladeira, Luz da Garagem) ficaram de fora por não terem objeto
  modelado ainda, não por limitação técnica.
- **Poll em vez de WebSocket.** Pra maquete pegar mudanças feitas pelo
  agendador ou por outra aba, precisava de alguma forma de sincronizar sem
  recarregar a página. Um `GET /api/dispositivos` consultado a cada 5
  segundos resolve isso com uma rota JSON simples, sem adicionar
  Flask-SocketIO nem infraestrutura nova — troca "tempo real de verdade"
  por "atualiza em até 5 segundos", aceitável pro que o projeto precisa.
- **Carregamento sob demanda.** As bibliotecas do Three.js (CDN) só são
  injetadas no DOM quando a aba "Maquete 3D" é aberta pela primeira vez —
  visitar o dashboard normalmente não paga o custo de carregar uma engine
  3D que a pessoa pode nunca abrir.

**Validado por:** smoke test (24/24, nada quebrou), e depois testes manuais
via `curl` simulando exatamente o que o clique na maquete faz — POST na
rota de toggle com o header `X-CSRFToken`, confirmando pela API que o
`ativo` do dispositivo mudou de verdade no banco. O clique dentro do
navegador (WebGL) em si não foi testado por aqui — não tem como rodar um
navegador de verdade neste ambiente — mas a lógica do clique é a mesma do
protótipo em Artifact que já tinha sido conferida visualmente antes.

## Como rodar

Ver `README.md` — nada mudou no fluxo (`pip install -r requirements.txt`,
`python seed.py`, `python app.py`). O `seed.py` agora recria duas semanas
de histórico e as automações de exemplo toda vez que é rodado.
