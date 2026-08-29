# Processo de desenvolvimento — sessão com IA

Este documento registra o processo de duas rodadas de trabalho feitas com
assistência de IA (Claude Code) em cima do projeto Casa 2050, incluindo o
que foi pedido, as decisões tomadas, os bugs encontrados e como cada coisa
foi validada. Serve como registro para a arguição individual, mostrando o
raciocínio por trás de cada mudança — não só o resultado final.

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
4. **Gráfico empilhado de consumo diário por cômodo** — usei o método de
   visualização de dados do próprio Claude Code (paleta categórica
   validada contra daltonismo, ordem de cor fixa por cômodo nunca por
   posição, legenda, marcas com espaçamento consistente).
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

## Como rodar

Ver `README.md` — nada mudou no fluxo (`pip install -r requirements.txt`,
`python seed.py`, `python app.py`). O `seed.py` agora recria duas semanas
de histórico e as automações de exemplo toda vez que é rodado.
