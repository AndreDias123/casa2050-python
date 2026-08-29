# Sprints do projeto

Organização retrospectiva do desenvolvimento do Casa 2050 em formato de
sprint — não é material de entrega da disciplina, é um registro de estudo
pra revisar como o projeto evoluiu e servir de referência de processo pro
próximo projeto do grupo.

Cada sprint corresponde a um bloco real de trabalho (não datas fixas de
calendário) e referencia o commit em que o resultado ficou registrado.

---

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

**Commit:** `Estado inicial: Casa 2050 - sistema inteligente de casa conectada`

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
- `.gitignore` (exclui `.venv/`, `__pycache__/`, `casa2050.db`).
- Repositório Git inicializado e publicado no GitHub.
- Este arquivo (`SPRINTS.md`), organizando o processo em formato de sprint
  pra servir de referência de metodologia.

**Commits:**
`Documenta o processo de desenvolvimento (PROCESS.md)` ·
`Organiza o desenvolvimento em sprints (SPRINTS.md)`

---

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
