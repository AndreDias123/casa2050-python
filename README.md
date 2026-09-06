# PULSE2050 — Sistema Inteligente

Trabalho do 4º semestre de Ciência da Computação pra ExpoTech 2026.2 (Missão
2050, categoria INTELLIGENCE). A proposta era montar o sistema por trás de
uma casa inteligente — não só a telinha, mas o banco de dados, a lógica de
programação orientada a objetos, autenticação, e um jeito de a casa "reagir"
de verdade ao que os dispositivos estão fazendo.

Documentação complementar: [`FLUXOGRAMA.md`](FLUXOGRAMA.md) mostra o fluxo
da aplicação em diagrama, [`PROCESS.md`](PROCESS.md) conta como fomos
construindo o projeto (e onde erramos e corrigimos no caminho), e
[`SPRINTS.md`](SPRINTS.md) organiza esse mesmo processo em sprints.

Também temos o design das telas (login, painel, detalhe do dispositivo,
energia e maquete 3D) no Figma, pra quem quiser ver isolado do código:
[PULSE2050 no Figma](https://www.figma.com/design/T8fPfgtPJPYLN3F3lGdegU/Projeto?node-id=2085-2&p=f&t=MSsG3kArnrFYGlrR-0).

## Com que a gente construiu

Python 3.10+, Flask, SQLAlchemy (com Flask-SQLAlchemy), Flask-Login e
SQLite pro banco. Optamos por Python porque é a linguagem que o grupo mais
domina, e Flask porque é leve o suficiente pra dar pra entender o projeto
inteiro sem um framework enorme no meio do caminho.

## Como rodar o projeto

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python seed.py                   # cria o banco (pulse2050.db) e popula com dados de exemplo
python app.py                    # sobe o servidor em http://localhost:5000
```

Depois é só abrir `http://localhost:5000` e entrar com uma das contas de
demonstração (elas também aparecem na própria tela de login):

| Perfil            | E-mail                  | Senha      |
|--------------------|--------------------------|-----------|
| Administrador      | admin@pulse2050.app      | admin123  |
| Usuário Comum       | comum@pulse2050.app      | comum123  |

Se quiser começar do zero de novo (apagar tudo e repopular), é só rodar
`python seed.py` outra vez — ele derruba e recria as tabelas.

## Como o projeto está organizado

```
app.py             monta a aplicação Flask e liga as partes (blueprints)
config.py          configurações gerais (banco, chave secreta, SMTP)
extensions.py      instâncias do SQLAlchemy e do Flask-Login
models.py          onde as classes/tabelas do banco estão definidas
auth.py            login e logout
main.py            painel, controle dos dispositivos e a API da maquete 3D
energia.py         painel de energia e o relatório por e-mail
services/
  energia.py       conta quanto de energia cada dispositivo gastou
  relatorios.py     monta (e manda, se tiver SMTP configurado) o relatório
  agendador.py     fica de olho no relógio e dispara as automações
templates/          as páginas HTML (Jinja2)
static/css/         o visual do projeto
static/js/casa3d.js a cena 3D da maquete
seed.py             popula o banco com cômodos, dispositivos, usuários,
                    automações e duas semanas de histórico de uso
```

## Modelagem de dados

A parte de que mais gostamos de pensar foi o `Dispositivo`. Em vez de criar
uma tabela separada pra cada tipo de aparelho (o que ia dar um monte de
JOIN toda hora), usamos uma técnica chamada Single Table Inheritance: existe
uma tabela só (`dispositivos`), e uma coluna (`tipo`) diz qual subclasse
Python aquele registro representa — `Luz`, `Porta`, `Janela`, `Camera`,
`TV`, `Eletrodomestico`, `RoboAspirador` ou `ArCondicionado`. Cada uma
dessas classes reescreve o método `status()` (e, quando faz sentido,
`ligar()`/`desligar()`) do seu próprio jeito — é o exercício de herança e
polimorfismo do trabalho acontecendo dentro do banco, não só num diagrama.

Cada vez que um dispositivo liga, desliga ou tem algum ajuste (tipo a
intensidade de uma luz), isso vira um registro na tabela `RegistroUso`, com
horário. É esse histórico que o `services/energia.py` usa pra calcular
quantas horas cada aparelho ficou ligado e multiplicar pela potência dele —
por isso os números do painel de energia são calculados de verdade, e não
inventados.

As automações (`Automacao` + `AutomacaoAcao`) ficaram um dos pontos que
mais evoluiu durante o projeto: no começo elas só ficavam salvas no banco,
sem disparar sozinhas. Depois colocamos o `services/agendador.py` rodando
junto com o Flask, checando a cada minuto se alguma automação bate com o
horário e o dia da semana — e quando bate, ele chama o mesmo `ligar()`/
`desligar()` que o botão da tela chama, então tudo entra no cálculo de
energia igualzinho. Dá pra ativar e desativar cada automação individual, e
o painel mostra qual vai disparar em seguida.

## Painel de energia

Além de mostrar quanto cada dispositivo consumiu, o painel compara a
semana atual com a anterior, projeta o gasto do mês inteiro no ritmo atual,
e tem um gráfico do consumo dia a dia por cômodo. Também colocamos um
alerta simples: se algum dispositivo consumiu bem mais que na semana
passada, o painel avisa e sugere olhar o agendamento dele.

## Maquete 3D

Além da tela normal (com os cards dos dispositivos), o painel tem uma
segunda aba chamada "Maquete 3D": uma casa em 3D (feita com Three.js) que
dá pra passear com a câmera e clicar nos dispositivos pra ligar/desligar de
verdade. Os 13 dispositivos do projeto têm um objeto correspondente na
cena.

O que achamos legal nessa parte não foi só o visual — é que ela usa
exatamente a mesma rota que os cards já usavam pra ligar/desligar
(`/dispositivo/<id>/alternar`), então não existe um caminho "especial" só
pra maquete. E como o agendador pode ligar algo sozinho, ou outra pessoa
pode mexer em outra aba, a maquete confere o estado do banco a cada 5
segundos (`GET /api/dispositivos`) pra se manter atualizada sem precisar
recarregar a página.

## Quem pode controlar o quê

Cada `Dispositivo` tem um campo `controlavel_por_comum`. O Administrador
sempre pode mexer em tudo; o Usuário Comum só nos dispositivos que estão
marcados como liberados. Essa regra vive num método só,
`Dispositivo.pode_controlar()`, e é usada tanto nas rotas (pra recusar a
ação, mesmo que alguém tente forçar) quanto na tela (o botão já aparece
desabilitado).

## Como testamos

Escrevemos um `smoke_test.py` que simula alguém usando o sistema de
verdade: login dos dois perfis, ligar/desligar dispositivo, tentar colocar
um valor inválido na intensidade da luz, ver o painel de energia, gerar um
relatório, tentar controlar algo sem permissão. São 24 checagens, e não
precisa nem subir o servidor — ele usa o cliente de teste do próprio
Flask. Pra rodar:

```bash
python seed.py        # garante um banco limpo pra testar
python smoke_test.py  # roda os 24 checks e mostra OK/FAIL de cada um
```

Esse arquivo já pegou bug de verdade durante o desenvolvimento — por
exemplo, a validação do horário de uma automação estava aceitando
`"25:99"` como se fosse um horário válido, e um `NameError` bobo (um
`import` esquecido) que só apareceu quando testamos de novo depois de
mexer no agendador.