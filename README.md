# Casa 2050 — Sistema Inteligente

Projeto do 4º semestre de Ciência da Computação (ExpoTech 2026.2 · Missão 2050,
categoria INTELLIGENCE) — arquitetura completa de uma smart home: modelagem
de dados, POO com herança/polimorfismo, autenticação com dois perfis,
persistência em banco relacional e um painel de energia calculado a partir
do histórico real de uso dos dispositivos.

## Stack

Python 3.10+, Flask, SQLAlchemy (via Flask-SQLAlchemy), Flask-Login, SQLite.

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python seed.py                   # cria o banco (casa2050.db) e popula com dados de exemplo
python app.py                    # sobe o servidor em http://localhost:5000
```

Abra `http://localhost:5000` e entre com uma das contas de demonstração
(também exibidas na tela de login):

| Perfil            | E-mail                | Senha      |
|--------------------|------------------------|-----------|
| Administrador      | admin@casa2050.app     | admin123  |
| Usuário Comum       | comum@casa2050.app     | comum123  |

Se quiser recomeçar do zero (apagar tudo e repopular), rode `python seed.py`
de novo — ele derruba e recria as tabelas.

## Estrutura

```
app.py             fábrica da aplicação Flask, registra as blueprints
config.py          configuração (banco, chave secreta, SMTP opcional)
extensions.py      instâncias do SQLAlchemy e do Flask-Login
models.py          modelagem de dados (ver abaixo)
auth.py            blueprint de login/logout
main.py             blueprint do painel e controle de dispositivos
energia.py          blueprint do painel de energia e do relatório por e-mail
services/
  energia.py       cálculo de kWh/custo a partir do histórico de uso
  relatorios.py     geração (e envio opcional via SMTP) do relatório semanal
templates/          páginas Jinja2 (herdam de base.html)
static/css/         folha de estilo (mesma identidade visual do protótipo)
seed.py             popula o banco com cômodos, dispositivos, usuários e uma
                    semana de histórico de uso sintético
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
permitindo que uma automação dispare ações em vários dispositivos.

`RelatorioEnviado` guarda um retrato congelado (kWh, custo, tarifa usada)
de cada relatório gerado, para que um relatório antigo não mude se a tarifa
mudar depois.

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

- **Automações não disparam sozinhas.** Elas são salvas no banco (CRUD
  funcionando), mas não há um agendador rodando em segundo plano ainda —
  daria pra ligar isso com `APScheduler`, chamando `dispositivo.ligar()`/
  `desligar()` no horário configurado.
- **Envio de e-mail real** funciona se você configurar `SMTP_HOST`,
  `SMTP_USER` e `SMTP_SENHA` como variáveis de ambiente (veja `config.py`).
  Sem isso, o relatório é gerado e você vê a pré-visualização na tela.
- Não há proteção CSRF nos formulários (`Flask-WTF` resolveria isso) —
  não chega a ser um requisito do projeto, mas é uma boa mencionar na
  arguição individual se perguntarem sobre segurança.
