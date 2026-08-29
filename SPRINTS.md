## Sprint 0 — Base do projeto

**Objetivo:** ter a arquitetura principal da smart home funcionando antes
de qualquer sprint de melhoria.

**Entregas:**
- Modelagem de dados com Single Table Inheritance (`Dispositivo` → `Luz`,
  `Porta`, `Janela`, `Camera`, `TV`, `Eletrodomestico`, `RoboAspirador`,
  `ArCondicionado`), cada subclasse com `status()`/`ligar()`/`desligar()`
  próprios — herança e polimorfismo aplicados no banco, não só no papel.
- Autenticação com dois perfis (Administrador / Usuário Comum) e permissão
  por dispositivo (`Dispositivo.pode_controlar()`).
- Painel de energia com kWh e custo calculados a partir do histórico real
  de uso (`RegistroUso`), não valores fixos.
- Automações (`Automacao`/`AutomacaoAcao`) com CRUD funcionando, mas ainda
  sem disparo automático.
- Relatório semanal por e-mail (com preview quando SMTP não configurado).
- `smoke_test.py` com 24 checks end-to-end.

**Backlog conhecido ao final da sprint** (registrado no próprio README):
automações não disparam sozinhas · sem proteção CSRF · e-mail depende de
SMTP configurado.

**Commit:** `Estado inicial: PULSE2050 - sistema inteligente de casa conectada`

---

## Sprint 1 — Automações disparando de verdade

**Objetivo:** resolver o item mais importante do backlog: fazer as
automações salvas no banco disparar sozinhas, sem depender de alguém
clicar num botão.

**Decisão de arquitetura:** `BackgroundScheduler` (APScheduler) rodando
dentro do próprio processo Flask, em vez de um serviço externo — mais
simples de rodar e demonstrar sem infraestrutura extra.

**Entregas:**
- `services/agendador.py`: checa a cada minuto se alguma automação ativa
  bate com horário/dia da semana (fuso `TIMEZONE`, padrão
  `America/Sao_Paulo`) e chama `dispositivo.ligar()`/`desligar()` — o
  mesmo método que o botão da UI usa, então o `RegistroUso` gerado entra
  no cálculo de energia normalmente.
- Guard contra o reloader do Flask subir o agendador duas vezes em modo
  debug (`WERKZEUG_RUN_MAIN`).
- `tzdata` adicionado às dependências (Windows não tem banco de fusos
  horários embutido, `zoneinfo` precisa do pacote pra funcionar).

**Validado por:** smoke test (24/24) + teste manual criando uma automação
com o horário atual e disparando a função do agendador diretamente, sem
esperar o minuto virar.

---

## Sprint 2 — Painel de energia inteligente

**Objetivo:** dar substância real à categoria INTELLIGENCE do projeto —
não só mostrar números, mas gerar um insight a partir deles.

**Entregas:**
- Alerta de consumo baseado em regra (`gerar_alerta()`): compara cada
  dispositivo com a semana anterior e aponta o que mais cresceu, acima de
  um limiar e com uma base mínima de comparação.
- Comparação semanal (variação %) e projeção mensal de custo.
- Gráfico empilhado de consumo diário por cômodo (paleta categórica de 5
  cores, ordem fixa por cômodo, legenda, tooltip por segmento).
- `seed.py` estendido para duas semanas de histórico (base de comparação
  da "semana anterior"), com o ar-condicionado ganhando uma tendência real
  de alta pra exercitar o alerta com um número plausível.

**Bug encontrado e corrigido durante a sprint:** o alerta inicialmente
calculava uma variação de **10794%** — o seed só tinha uma semana de
histórico, então o período de comparação ficava quase vazio e a divisão
explodia. Corrigido exigindo uma base mínima de consumo no período
anterior antes de calcular variação, além de estender o histórico do seed.

---

## Sprint 3 — Automação de UI, login e segurança

**Objetivo:** fechar os itens de experiência e o gap de segurança que
ainda restavam.

**Entregas:**
- Toggle de ativar/desativar cada automação individualmente (nova rota
  `alternar_automacao`), respeitando a mesma permissão de controle do
  dispositivo.
- Banner "próxima automação" no dashboard (`proxima_automacao()` +
  `rotulo_quando()` em `services/agendador.py`).
- Filtro por cômodo no dashboard (chips + JS puro, sem framework).
- Login: botões "continuar como Administrador/Usuário Comum" e "lembrar
  de mim" (`Flask-Login remember=True`).
- Proteção CSRF (`Flask-WTF`) nos 8 formulários POST do app.
- `seed.py`: automações de exemplo (não existia nenhuma antes, então o
  banner e o toggle não tinham o que mostrar numa instalação nova).

**Bug encontrado e corrigido durante a sprint:** `NameError: timedelta` em
`services/agendador.py` (função nova usando `timedelta` sem importar) —
pego pelo smoke test na primeira execução, corrigido na hora.

**Commit (sprints 1-3, um único commit de features):**
`Automacoes disparam de verdade + painel de energia inteligente + UI/seguranca`

---

## Sprint 4 — Documentação e publicação

**Objetivo:** deixar registro do processo e publicar o projeto.

**Entregas:**
- `PROCESS.md`: relato do processo de desenvolvimento (decisões, bugs
  encontrados/corrigidos, como cada coisa foi validada).
- `.gitignore` (exclui `.venv/`, `__pycache__/`, `pulse2050.db`).
- Repositório Git inicializado e publicado no GitHub.
- Este arquivo (`SPRINTS.md`), organizando o processo em formato de sprint
  pra servir de referência de metodologia.

**Commits:**
`Documenta o processo de desenvolvimento (PROCESS.md)` ·
`Organiza o desenvolvimento em sprints (SPRINTS.md)`

---

## Sprint 5 — Conferência contra o edital oficial

**Objetivo:** parar de avaliar o projeto "no olho" e checar item por item
contra o roteiro oficial da categoria INTELLIGENCE (ExpoTech 2026.2,
4º semestre CDC) pra garantir que nada estava faltando antes da avaliação
individual em sala.

**O que o edital pede, literalmente, em "Requisitos do Projeto":**
modelagem de dados, fluxograma, interface de usuário, validação de dados,
linguagem (Rust/Python/Java), integração front-end/back-end, autenticação,
banco relacional, perfis de usuário com permissões distintas. Mais os
"Conceitos e Critérios Abordados": UX/UI, desenvolvimento na linguagem
escolhida, POO (classes/herança/polimorfismo/encapsulamento), estratégia
de estruturas de dados, engenharia de software.

**Gaps encontrados na conferência:**
- **Fluxograma: ausente por completo.** Item explícito da lista, checkbox
  literal, nunca foi feito.
- **Estratégia de estruturas de dados: implícita, não documentada.** O
  código já fazia escolhas conscientes (dict pra lookup O(1), set pra
  checagem de dia da semana, ordenação delegada ao banco), mas em lugar
  nenhum isso estava explicado — se perguntado na arguição individual
  ("por que um dict aqui?"), não havia resposta preparada por escrito.
- Todos os outros 8 requisitos e os outros 4 critérios já estavam
  atendidos pelo trabalho das sprints anteriores.

**Entregas da sprint:**
- `FLUXOGRAMA.md`: fluxo completo da aplicação em diagrama (Mermaid,
  renderiza direto no GitHub), cobrindo os dois pontos de entrada de
  eventos no sistema — uma pessoa pela UI e o agendador rodando sozinho —
  e todas as checagens de permissão/validação no caminho.
- `PROCESS.md`: nova seção "Estruturas de dados" justificando cada escolha
  já existente no código (nenhuma estrutura nova foi criada — só a
  explicação do porquê de cada uma).
- `README.md`: linkando os três documentos complementares logo na
  introdução.

**Nota sobre a regra de equipe (3 a 5 integrantes, avaliação individual):**
como a nota é individual e qualquer integrante pode ser questionado sobre
qualquer parte do projeto, os documentos `PROCESS.md`/`SPRINTS.md` viram
material de estudo real pra equipe toda — não só um registro do que foi
feito, mas a base pra cada pessoa conseguir explicar qualquer trecho do
código na arguição, mesmo uma parte que não foi ela quem escreveu.

## Sprint 6 — Maquete 3D interativa e integrada

**Objetivo:** dar ao projeto um diferencial visual de verdade — não só um
mockup pra mostrar a ideia, mas uma segunda forma de controlar a casa,
dentro do próprio painel, ligada ao banco de dados de verdade.

**Caminho até aqui (três protótipos, um final):**
1. Mockup em Artifact de uma planta isométrica (2.5D) clicável, pra validar
   se "clicar num ícone e ver a casa reagir" valia o esforço antes de
   construir de verdade.
2. Um tour 3D em Three.js (câmera automática passeando pela casa) — bonito,
   mas sem interação nenhuma ainda.
3. Os dois combinados: a cena 3D do tour ganhou os gatilhos clicáveis do
   mockup isométrico — luzes, TV, robô aspirador, porta da garagem etc.,
   todos reagindo a clique.

**Depois disso, integração de verdade com o Flask:**
- Nova aba "Maquete 3D" no dashboard, ao lado dos cards — carrega a cena só
  quando aberta pela primeira vez.
- Clicar num dispositivo na cena chama a mesma rota
  `/dispositivo/<id>/alternar` que os cards já usavam — mesma permissão,
  mesmo registro de uso, sem lógica duplicada.
- Nova rota `GET /api/dispositivos` (JSON) que a maquete consulta a cada 5
  segundos, pra pegar mudanças feitas pelo agendador ou por outra aba sem
  precisar recarregar a página.

**Entregas:**
- `static/js/casa3d.js` — a cena 3D, conectada ao banco.
- `main.py` — rota `/api/dispositivos` e os dados da maquete no contexto
  do dashboard.
- `templates/dashboard.html` — aba nova, carregamento sob demanda das
  bibliotecas do Three.js.
- `templates/base.html` — meta tag com o token CSRF, pra chamadas AJAX.
- `README.md`/`PROCESS.md` — documentando a decisão de reaproveitar a rota
  de toggle existente em vez de duplicar lógica, e o poll em vez de
  WebSocket.

**Validado por:** smoke test (24/24) e teste manual via `curl` reproduzindo
exatamente a chamada que o clique na maquete faz (POST com o header
`X-CSRFToken`), confirmando pela API que o dispositivo mudou de estado no
banco de verdade.

## O que aproveitar disso pro próximo projeto do grupo

- **Cadência:** cada sprint acima corresponde a "uma lacuna resolvida por
  vez" — dá pra manter esse tamanho de escopo (uma dor de cada vez, testada
  antes de passar pra próxima) com 4 pessoas em paralelo, uma por
  frente/lacuna.
- **Definition of Done que funcionou aqui:** rodar o smoke test depois de
  cada mudança pegou dois bugs reais antes de irem pra produção — vale
  manter testes automatizados rodando a cada sprint, não só no final.
- **O que faltou nesse projeto e vale planejar desde o início no próximo:**
  fluxo de git de equipe de verdade (branch por pessoa/feature, PR com
  review antes de mergear) — aqui foi tudo em cima de `main` porque era
  uma pessoa só.
