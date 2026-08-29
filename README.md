# PULSE2050 — Sistema Inteligente

Projeto do 4º semestre de Ciência da Computação (ExpoTech 2026.2 · Missão 2050,
categoria INTELLIGENCE) — arquitetura completa de uma smart home: modelagem
de dados, POO com herança/polimorfismo, autenticação com dois perfis,
persistência em banco relacional e um painel de energia calculado a partir
do histórico real de uso dos dispositivos.

Documentação complementar: [`FLUXOGRAMA.md`](FLUXOGRAMA.md) (fluxo completo
da aplicação), [`PROCESS.md`](PROCESS.md) (processo de desenvolvimento,
decisões e estruturas de dados) e [`SPRINTS.md`](SPRINTS.md) (o mesmo
processo organizado em sprints).

## Stack

Python 3.10+, Flask, SQLAlchemy (via Flask-SQLAlchemy), Flask-Login, SQLite.

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python seed.py                   # cria o banco (pulse2050.db) e popula com dados de exemplo
python app.py                    # sobe o servidor em http://localhost:5000
```

Abra `http://localhost:5000` e entre com uma das contas de demonstração
(também exibidas na tela de login):

| Perfil            | E-mail                | Senha      |
|--------------------|------------------------|-----------|
| Administrador      | admin@pulse2050.app     | admin123  |
| Usuário Comum       | comum@pulse2050.app     | comum123  |

Se quiser recomeçar do zero (apagar tudo e repopular), rode `python seed.py`
de novo — ele derruba e recria as tabelas.

## Estrutura

```
app.py             fábrica da aplicação Flask, registra as blueprints
config.py          configuração (banco, chave secreta, SMTP opcional)
extensions.py      instâncias do SQLAlchemy e do Flask-Login
models.py          modelagem de dados (ver abaixo)
auth.py            blueprint de login/logout
main.py            blueprint do painel e controle de dispositivos
energia.py         blueprint do painel de energia e do relatório por e-mail
services/
  energia.py       cálculo de kWh/custo a partir do histórico de uso
  relatorios.py     geração (e envio opcional via SMTP) do relatório semanal
  agendador.py     dispara automações no horário certo (ver seção abaixo)
templates/          páginas Jinja2 (herdam de base.html)
static/css/         folha de estilo (mesma identidade visual do protótipo)
seed.py             popula o banco com cômodos, dispositivos, usuários,
                    automações de exemplo e duas semanas de histórico de uso
                    sintético
```

## Modelagem de dados

`Dispositivo` é mapeado com **Single Table Inheritance**: uma tabela só
(`dispositivos`), discriminada pela coluna `tipo`, com uma subclasse Python
por tipo de dispositivo (`Luz`, `Porta`, `Janela`, `Camera`, `TV`,
`Eletrodomestico`, `RoboAspirador`, `ArCondicionado`). Cada subclasse
sobrescreve `status()` e, quando faz sentido, `ligar()`/`desligar()` — é
isso que materializa herança e polimorfismo no banco, não só no papel.

`RegistroUso` guarda cada evento (ligou/desligou/ajustou) com timestamp.
`services/energia.py` usa esse histórico para calcular quantas horas cada
dispositivo ficou ligado num período e multiplica pela potência (Watts) —
por isso o painel de energia mostra números calculados de verdade, não
valores fixos.

`Automacao` + `AutomacaoAcao` modelam rotinas (ex.: "acender às 18:30"),
permitindo que uma automação dispare ações em vários dispositivos. Elas
disparam de verdade: `services/agendador.py` sobe um `BackgroundScheduler`
(APScheduler) junto com o Flask que checa a cada minuto se alguma automação
ativa bate com o horário e o dia da semana atuais (fuso `TIMEZONE`, padrão
`America/Sao_Paulo`) e chama `dispositivo.ligar()`/`desligar()` — o mesmo
código que uma pessoa aciona pelo botão, então o `RegistroUso` gerado
(`usuario=None`) entra no cálculo de energia normalmente. Cada automação pode
ser ativada/desativada individualmente na tela do dispositivo, e o painel
mostra a próxima automação a disparar.

`RelatorioEnviado` guarda um retrato congelado (kWh, custo, tarifa usada)
de cada relatório gerado, para que um relatório antigo não mude se a tarifa
mudar depois.

## Painel de energia

Além do consumo e custo do período, o painel compara a semana atual com a
anterior (variação %), projeta o custo do mês no ritmo atual, e mostra um
gráfico empilhado do consumo diário por cômodo dos últimos 7 dias. Também
gera um alerta simples baseado em regra: se algum dispositivo consumiu
bem mais essa semana que na anterior (acima de um limiar, com uma base de
comparação mínima pra não disparar em cima de ruído), o painel aponta qual
e sugere ajustar o agendamento — é a peça que mais materializa a categoria
INTELLIGENCE no projeto, mesmo sendo uma regra simples e não um modelo de
ML (não fazia sentido treinar algo em cima do volume de dados de uma casa
simulada).

## Permissões

Cada `Dispositivo` tem `controlavel_por_comum` (bool). O Administrador
sempre pode controlar tudo; o Usuário Comum só os dispositivos marcados
como liberados — a regra vive em `Dispositivo.pode_controlar()` e é
aplicada tanto nas rotas (retorna erro sem a permissão) quanto na tela
(o botão aparece desabilitado).

## Testes

`smoke_test.py` exercita as rotas reais (login dos dois perfis, dashboard,
alternar dispositivo, validação de intensidade, painel de energia, geração
de relatório, bloqueio de permissão) usando o test client do Flask — não
precisa do servidor rodando. Para conferir que está tudo funcionando depois
de qualquer alteração no código:

```bash
python seed.py        # garante um banco limpo
python smoke_test.py  # roda os 24 checks e imprime OK/FAIL de cada um
```

Esse arquivo já foi rodado durante o desenvolvimento e pegou (e corrigiu)
bugs reais: validação de horário de automação aceitando `"25:99"` como
válido, e um warning do SQLAlchemy na geração do relatório.

## O que ainda é só esqueleto (próximos passos, se sobrar tempo)

- **Envio de e-mail real** funciona se você configurar `SMTP_HOST`,
  `SMTP_USER` e `SMTP_SENHA` como variáveis de ambiente (veja `config.py`).
  Sem isso, o relatório é gerado e você vê a pré-visualização na tela.
- **Dias da semana da automação.** O modelo já suporta `dias_semana` (ex.:
  `"seg,qua,sex"`, interpretado por `services/agendador.py`), mas o
  formulário de criar automação só permite todo dia — falta o seletor de
  dias na tela.
- Os botões "continuar como Administrador/Usuário Comum" na tela de login
  são propositalmente uma conveniência de demonstração (as mesmas contas já
  aparecem em texto puro logo abaixo) — não seriam apropriados assim numa
  aplicação real com contas de verdade.
