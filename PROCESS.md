# Como o projeto foi evoluindo

Esse documento é o nosso registro de como fomos construindo o PULSE2050 —
não só o que ficou pronto, mas o caminho até chegar lá: o que a gente
tentou, o que deu errado antes de dar certo, e por que escolhemos um jeito
de fazer em vez de outro. A ideia é que qualquer um do grupo consiga usar
isso pra estudar antes da arguição individual, mesmo numa parte do código
que não foi ele quem escreveu.

## De onde a gente partiu

O projeto já chegou com a base pronta: a modelagem de dados, a herança e
polimorfismo do `Dispositivo`, o login com dois perfis, e o painel de
energia calculando em cima do histórico real de uso. O próprio README já
apontava três coisas que faltavam: as automações não disparavam sozinhas,
não tinha proteção contra CSRF nos formulários, e o envio de e-mail
dependia de configurar SMTP.

## Fazendo as automações funcionarem de verdade

A primeira coisa que resolvemos foi a lacuna mais óbvia: automação salva no
banco, mas que nunca dispara sozinha. Pensamos em algumas formas de
resolver isso e optamos por usar o APScheduler rodando junto do próprio
processo do Flask (em vez de montar um serviço separado) — é bem mais
simples de rodar e de explicar, e não precisa de nenhuma infraestrutura
extra que a gente não teria como manter.

A parte que deu mais trabalho aqui não foi o agendador em si, foi um
detalhe de fuso horário: o resto do sistema trabalha em UTC, mas o horário
que a pessoa digita numa automação ("18:30") é óbvio que é hora local dela.
Então criamos uma configuração de `TIMEZONE` (padrão `America/Sao_Paulo`) e
usamos isso pra comparar direito. E descobrimos no caminho que o Windows
não vem com um banco de fusos horários embutido — sem o pacote `tzdata`
instalado, o Python simplesmente não sabe o que é "America/Sao_Paulo" e dá
erro.

Outra pegadinha: como o Flask em modo de desenvolvimento sobe dois
processos (um só de observador, outro que realmente atende), sem cuidado
o agendador ia rodar duas vezes ao mesmo tempo e disparar cada automação
duas vezes por minuto. Resolvemos isso checando uma variável de ambiente
que só existe no processo "de verdade".

Testamos criando uma automação com o horário de agora mesmo e chamando a
função do agendador na mão, sem esperar o relógio virar — e confirmamos
que o dispositivo realmente ligava e ficava registrado no banco.

## Deixando o painel de energia mais inteligente

Depois de resolver as automações, focamos em dar mais substância pra
categoria do projeto (INTELLIGENCE). Não bastava só mostrar número de kWh
— queria mostrar algum tipo de análise em cima disso. Então implementamos:

- Uma comparação da semana atual com a anterior (quanto cresceu ou caiu, em
  porcentagem);
- Uma projeção de quanto isso vai dar de custo no mês inteiro, no ritmo
  atual;
- Um alerta que aponta o dispositivo que mais aumentou o consumo — se
  passar de um certo limite;
- Um gráfico do consumo por dia, separado por cômodo.

Um bug engraçado apareceu aqui: no primeiro teste, o alerta calculou que um
dispositivo tinha aumentado o consumo em **10794%**. O motivo era simples —
os dados de exemplo (`seed.py`) só tinham uma semana de histórico, então a
"semana anterior" usada como comparação praticamente não tinha nenhum dado,
e dividir por um número quase zero explode a porcentagem. Corrigimos de
duas formas: o alerta passou a exigir uma quantidade mínima de consumo na
semana anterior antes de calcular a variação, e estendemos o histórico de
exemplo pra duas semanas.

## Deixando a experiência mais completa

Com o núcleo funcionando, fomos atrás de fechar pontas soltas de uso e de
segurança:

- Cada automação ganhou um botão pra ativar/desativar ela sozinha, sem
  precisar apagar e criar de novo;
- O painel passou a mostrar qual é a próxima automação a disparar;
- Adicionamos um filtro por cômodo no painel;
- O login ganhou botões de "continuar como Administrador/Usuário Comum"
  (só pra facilitar testar) e a opção de "lembrar de mim";
- E, o mais importante do ponto de vista de segurança: adicionamos proteção
  contra CSRF em todos os formulários com o Flask-WTF.

Nessa etapa também apareceu um erro bobo — uma função nova
(`proxima_automacao`) usando `timedelta` sem ter importado. O smoke test
pegou isso na primeira rodada depois da mudança, e corrigimos na hora.

## Conferindo contra o que o edital pedia

Depois de um tempo focados em construir, paramos pra checar item por item
contra o roteiro oficial da categoria INTELLIGENCE, em vez de confiar só na
nossa impressão de que "tava tudo pronto". E encontramos dois furos:

- **Não tinha fluxograma nenhum.** É um item explícito da lista de
  requisitos, e simplesmente não tínhamos feito ainda.
- **A estratégia de estrutura de dados nunca foi explicada em lugar
  nenhum.** O código já fazia escolhas conscientes (por exemplo, usar um
  dicionário pra buscar a cor de um cômodo em vez de percorrer uma lista
  toda vez), mas nunca escrevemos o porquê — e se alguém perguntasse isso
  na arguição, não teríamos uma resposta pronta.

Resolvemos os dois: criamos o `FLUXOGRAMA.md` com o fluxo completo da
aplicação, e acrescentamos uma seção no fim deste documento explicando as
escolhas de estrutura de dados que já existiam no código.

## A maquete 3D

Essa foi a parte mais divertida de fazer, e também a que passou por mais
versões até chegar no formato final. Primeiro pensamos em fazer a casa em
3D de verdade, mas achamos que o risco de não terminar a tempo era alto
demais pra um "extra" — então fizemos um protótipo mais simples primeiro,
uma planta baixa meio 2.5D, só pra testar a ideia de "clicar num ícone e
ver a casa reagir". Gostamos do resultado, e aí juntamos essa interação com
uma cena 3D de verdade (com Three.js) que já tínhamos experimentado à
parte, com uma câmera passeando automaticamente pela casa.

Depois veio a parte que mais importa pro projeto: conectar isso ao Flask
de verdade, e não deixar só como uma demonstração isolada. Pra isso:

- Fizemos a maquete usar a **mesma rota** que os cards já usavam pra
  ligar/desligar um dispositivo, em vez de criar uma rota nova só pra ela
  — assim a regra de permissão e o registro de uso continuam sendo os
  mesmos, sem duplicar lógica em dois lugares;
- Criamos uma rota nova só de consulta (`/api/dispositivos`, em formato
  JSON) que a maquete confere a cada 5 segundos, pra pegar mudanças que
  vieram de uma automação ou de outra pessoa mexendo em outra aba;
- Deixamos as bibliotecas do Three.js (que são pesadas) carregando só
  quando a pessoa realmente abre a aba da maquete, pra não deixar o painel
  normal mais lento à toa;
- No fim, completamos os três dispositivos que ainda não tinham objeto na
  cena (Câmera da Sala, Geladeira e Luz da Garagem), então hoje os 13
  dispositivos do projeto aparecem lá.

## Estruturas de dados — o porquê de cada escolha

Não criamos nenhuma estrutura de dados do zero (não fazia sentido
reinventar uma árvore ou uma tabela hash quando o Python e o SQLAlchemy já
dão ferramentas prontas pra isso), mas cada uso delas foi pensado, não foi
só a primeira coisa que funcionou:

- **Dicionário pra buscar informação por cômodo** (a cor de cada cômodo no
  gráfico, o total de consumo por cômodo): a alternativa seria uma lista
  de pares e percorrer ela toda vez que precisasse do valor de um cômodo
  específico. Com dicionário, cada busca é praticamente instantânea, e
  como a mesma informação é consultada várias vezes numa página só, a
  diferença é real mesmo numa casa pequena.
- **Conjunto (`set`) pra checar o dia da semana da automação:** em vez de
  guardar os dias como uma lista separada por vírgula e checar um por um,
  transformamos isso num `set` — como essa checagem roda a cada minuto
  (é o agendador conferindo se alguma automação bate com agora), faz
  sentido que ela seja o mais rápida possível.
- **Deixamos o próprio banco de dados ordenar os registros**, em vez de
  buscar tudo e ordenar de novo em Python — o SQLite já faz isso de forma
  eficiente, então repetir o trabalho em Python seria desperdício.
- **Lista comum com ordenação simples pra ranquear o consumo dos
  dispositivos:** como uma casa tem só algumas dezenas de dispositivos no
  máximo, não fazia sentido usar uma estrutura mais sofisticada (tipo uma
  fila de prioridade) só pra parecer mais avançado — ordenar do jeito mais
  simples já resolve bem nessa escala.
- **A escolha de Single Table Inheritance** pro `Dispositivo`, em vez de
  uma tabela por tipo: a alternativa evitaria algumas colunas que só fazem
  sentido pra certos tipos de aparelho, mas ia exigir um JOIN toda vez que
  quiséssemos ver os dispositivos de um cômodo — e essa é justamente a
  consulta mais comum do sistema inteiro (acontece toda vez que o painel
  carrega). Preferimos simplicidade na consulta mais frequente.

## Como testamos tudo isso

Rodamos o `smoke_test.py` depois de cada mudança relevante — ele simula
alguém de verdade usando o sistema (login, ligar dispositivo, gerar
relatório, tentar burlar permissão) e imprime OK/FAIL de cada checagem. Foi
esse arquivo que pegou os dois bugs mencionados acima antes de virarem
problema. Pra funcionalidades que dependem de tempo (o agendador, por
exemplo), também fizemos testes manuais chamando a função direto, sem
esperar o relógio virar de verdade. E, pra maquete 3D, testamos a
integração com o back-end simulando via linha de comando exatamente a
chamada que um clique faz (com o token de segurança certo), confirmando
que o estado realmente mudava no banco — o clique dentro do navegador em
si (a parte gráfica) foi conferido visualmente, já que isso depende de
rodar num navegador de verdade.
