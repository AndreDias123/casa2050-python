# O projeto em sprints

Esse documento organiza o desenvolvimento do PULSE2050 em sprints, mostrando
como o projeto foi crescendo, período por período. Cada sprint aqui
representa um pedaço real de trabalho, não uma data fixa de calendário.

---

## Sprint 0 — A base do projeto

O que já estava pronto antes da gente começar a mexer:

- A modelagem de dados com herança (`Dispositivo` e suas subclasses — Luz,
  Porta, Janela, Câmera, TV, Eletrodoméstico, Robô Aspirador,
  Ar-condicionado), cada uma com seu próprio jeito de responder
  `status()`/`ligar()`/`desligar()`.
- Login com dois perfis (Administrador e Usuário Comum), com permissão por
  dispositivo.
- Painel de energia calculando kWh e custo em cima do histórico real de
  uso, não valor fixo.
- Automações salvas no banco (dava pra criar), mas sem disparo automático.
- Relatório semanal por e-mail (com prévia quando não tem SMTP
  configurado).
- Um arquivo de teste (`smoke_test.py`) com 24 checagens automáticas.

O que faltava, pelo próprio README do projeto: as automações não
disparavam sozinhas, não tinha proteção contra CSRF, e o e-mail dependia de
configurar SMTP.

---

## Sprint 1 — Fazendo as automações disparar sozinhas

Esse era o item mais importante da lista de pendências. A solução foi usar
o APScheduler rodando junto do Flask, checando a cada minuto se alguma
automação bate com o horário e o dia atual, e chamando o mesmo
`ligar()`/`desligar()` que o botão da tela usa.

No caminho, resolvemos um problema de fuso horário (o resto do sistema usa
UTC, mas o horário da automação é hora local — criamos uma configuração
`TIMEZONE`), descobrimos que o Windows precisa do pacote `tzdata` pra
entender fusos horários, e evitamos que o agendador rodasse duas vezes ao
mesmo tempo por causa do modo de desenvolvimento do Flask.

Testamos criando uma automação com o horário de agora e chamando a função
do agendador na mão, sem esperar o relógio virar — funcionou.

---

## Sprint 2 — Deixando o painel de energia mais inteligente

Aqui o foco foi dar mais conteúdo real pra categoria INTELLIGENCE do
projeto. Adicionamos: comparação com a semana anterior, projeção do gasto
do mês, um alerta que aponta o dispositivo que mais aumentou o consumo, e
um gráfico do consumo diário por cômodo.

Durante o teste, o alerta calculou uma variação de consumo de **10794%**
num dispositivo — bug real, causado por só termos uma semana de dados de
exemplo (a "semana anterior" usada pra comparar praticamente não tinha
dado nenhum). Corrigimos exigindo uma base mínima de comparação, e
estendendo os dados de exemplo pra duas semanas.

---

## Sprint 3 — Terminando a experiência e a segurança

- Cada automação ganhou um botão de ativar/desativar.
- O painel passou a mostrar a próxima automação a disparar.
- Adicionamos filtro por cômodo no painel.
- O login ganhou atalhos pra entrar como Administrador/Usuário Comum (só
  facilita testar) e a opção "lembrar de mim".
- Colocamos proteção contra CSRF em todos os formulários (Flask-WTF).

Um bug bobo apareceu aqui — uma função nova usando `timedelta` sem
importar. O smoke test acusou isso na hora e corrigimos rápido.

---

## Sprint 4 — Documentando e publicando

Criamos o `PROCESS.md` contando o processo de desenvolvimento, o
`.gitignore`, inicializamos o repositório Git e publicamos no GitHub. Esse
próprio arquivo (`SPRINTS.md`) também nasceu nessa etapa.

---

## Sprint 5 — Conferindo contra o edital

Paramos de confiar só na nossa impressão de "acho que já tá tudo pronto" e
checamos item por item contra o roteiro oficial da categoria INTELLIGENCE.
Encontramos dois furos: não tínhamos fluxograma nenhum (item explícito da
lista), e nunca tínhamos escrito o porquê das escolhas de estrutura de
dados que o código já usava.

Resolvemos os dois: criamos o `FLUXOGRAMA.md` com o fluxo completo da
aplicação, e escrevemos a explicação das estruturas de dados no
`PROCESS.md`.

Assim, qualquer um do grupo consegue explicar qualquer parte do projeto,
não só quem escreveu aquele trecho específico.

---

## Sprint 6 — A maquete 3D

Essa foi a sprint que deu mais trabalho de decisão, porque passamos por
alguns protótipos antes de chegar no formato final:

1. Primeiro um mockup mais simples (planta baixa 2.5D) só pra testar se a
   ideia de "clicar num dispositivo e ver a casa reagir" valia o esforço.
2. Depois um passeio 3D pela casa (Three.js), bonito mas sem interação
   nenhuma ainda.
3. Juntamos os dois: a cena 3D ganhou os cliques interativos do primeiro
   protótipo.

E então veio a parte que mais importa: conectar isso ao Flask de verdade.
A maquete usa a mesma rota que os cards já usavam pra ligar/desligar um
dispositivo (nada de lógica duplicada), e criamos uma rota nova só de
consulta que ela confere a cada 5 segundos, pra pegar mudanças vindas do
agendador ou de outra pessoa mexendo em outra aba. As bibliotecas 3D só
carregam quando a aba é aberta, pra não deixar o painel normal mais lento.

No fim, completamos os três dispositivos que ainda faltavam objeto na
cena (Câmera da Sala, Geladeira, Luz da Garagem) — hoje os 13 dispositivos
do projeto aparecem na maquete.

**Testamos** rodando o smoke test de novo (nada quebrou) e simulando via
linha de comando exatamente a chamada que um clique na maquete faz,
confirmando que o dispositivo realmente muda de estado no banco.
