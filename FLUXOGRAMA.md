# Fluxograma da aplicação

Esse diagrama mostra o caminho completo que uma ação percorre no
PULSE2050, desde quem inicia ela até o que acontece no banco de dados.
Tem duas formas de uma ação começar: uma pessoa usando a interface (login,
painel, maquete 3D) ou o agendador rodando sozinho em segundo plano,
disparando uma automação sem ninguém clicar em nada.

```mermaid
flowchart TD
    Start([Acessa a aplicação]) --> Auth{Sessão\nautenticada?}

    Auth -- não --> Login[/Tela de login/]
    Login --> Cred[Envia e-mail + senha]
    Cred --> Valida{Credenciais\nválidas?}
    Valida -- não --> LoginErro[Mensagem de erro]
    LoginErro --> Login
    Valida -- sim --> Sessao[Cria sessão\nFlask-Login]
    Sessao --> Dashboard

    Auth -- sim --> Dashboard[/Dashboard: cômodos e dispositivos/]

    Dashboard --> Filtro[Filtra por cômodo]
    Filtro --> Dashboard
    Dashboard --> Escolhe{O que fazer?}

    Escolhe -- abrir dispositivo --> Detalhe[/Detalhe do dispositivo/]
    Escolhe -- ver energia --> Energia
    Escolhe -- alternar dispositivo direto no card --> PermToggle
    Escolhe -- abrir aba Maquete 3D --> Maquete3D

    Maquete3D[/Maquete 3D: cena Three.js/] --> Clique3D{Clicou num\ndispositivo\nmodelado?}
    Clique3D -- não --> Maquete3D
    Clique3D -- sim --> PermToggle

    Detalhe --> AcaoDet{Ação}

    AcaoDet -- ligar/desligar --> PermToggle{Perfil pode\ncontrolar?}
    PermToggle -- não --> Bloqueado[Erro: sem permissão]
    Bloqueado --> Dashboard
    PermToggle -- sim --> Alterna[dispositivo.alternar]
    Alterna --> Registra1[(RegistroUso\nusuario = pessoa logada)]
    Registra1 --> Dashboard

    AcaoDet -- ajustar intensidade (Luz) --> ValidaInt{Número\ninteiro 1-100?}
    ValidaInt -- não --> ErroInt[Rejeita, mantém valor]
    ErroInt --> Detalhe
    ValidaInt -- sim --> Ajusta[ajustar_intensidade]
    Ajusta --> Registra2[(RegistroUso\nevento=ajustou)]
    Registra2 --> Detalhe

    AcaoDet -- criar automação --> ValidaHor{Nome + horário\nHH:MM válidos?}
    ValidaHor -- não --> ErroForm[Mensagem de erro]
    ErroForm --> Detalhe
    ValidaHor -- sim --> SalvaAuto[(Automacao +\nAutomacaoAcao)]
    SalvaAuto --> Detalhe

    AcaoDet -- ativar/desativar automação --> ToggleAuto{Perfil pode\ncontrolar?}
    ToggleAuto -- não --> Bloqueado
    ToggleAuto -- sim --> AlternaAuto[automacao.ativa = not ativa]
    AlternaAuto --> Detalhe

    AcaoDet -- admin: mudar permissão --> IsAdmin{É\nadministrador?}
    IsAdmin -- não --> Bloqueado
    IsAdmin -- sim --> MudaPerm[controlavel_por_comum = not X]
    MudaPerm --> Detalhe

    Energia[/Painel de energia/] --> Calc[kwh_consumidos por dispositivo\na partir do RegistroUso]
    Calc --> Comp[Compara com a semana anterior]
    Comp --> Alerta{Algum dispositivo\ncresceu acima\ndo limiar?}
    Alerta -- sim --> Aviso[Mostra alerta de consumo]
    Alerta -- não --> SemAviso[Sem alerta]
    Aviso --> Grafico[Gráfico diário por cômodo]
    SemAviso --> Grafico
    Grafico --> Relatorio{Gerar relatório\npor e-mail?}
    Relatorio -- sim --> SMTP{SMTP\nconfigurado?}
    SMTP -- sim --> Envia[Envia e-mail de verdade]
    SMTP -- não --> Preview[Só gera e mostra preview]
    Envia --> SalvaRel[(RelatorioEnviado)]
    Preview --> SalvaRel
    SalvaRel --> Energia

    subgraph BG [Em paralelo — sem intervenção humana]
        direction TB
        Tick([A cada minuto]) --> Bate{Alguma automação\nativa bate com\nhorário + dia atual?}
        Bate -- não --> Tick
        Bate -- sim --> Dispara[dispositivo.ligar / desligar]
        Dispara --> Registra3[(RegistroUso\nusuario = None)]
        Registra3 --> Tick
    end

    Registra3 -.alimenta.-> Calc
    Registra1 -.alimenta.-> Calc
    Registra2 -.alimenta.-> Calc

    subgraph POLL [Enquanto a Maquete 3D estiver aberta]
        direction TB
        PollTick([Timer 5s]) --> Consulta[GET /api/dispositivos]
        Consulta --> Diff{Algum ativo\nmudou desde\no último poll?}
        Diff -- não --> PollTick
        Diff -- sim --> AtualizaCena[Atualiza a cena 3D + toast]
        AtualizaCena --> PollTick
    end
```

## O que vale reparar nesse fluxo

- **Tem duas formas de o histórico de uso (`RegistroUso`) ser criado**: uma
  pessoa mexendo pela interface, ou o agendador disparando uma automação
  sozinho. Os dois casos alimentam o mesmo cálculo de energia — não
  criamos um caminho separado só pra automação, ela usa exatamente a mesma
  lógica que um clique humano usaria.
- **Toda ação de controle passa pela mesma checagem de permissão** antes
  de mudar qualquer coisa. Ela aparece três vezes no desenho (ligar/desligar
  dispositivo, ativar automação, mudar permissão) porque é literalmente a
  mesma regra sendo usada em três lugares diferentes do sistema, não uma
  regra reescrita três vezes.
- **Todo formulário é validado antes de mexer no banco** — intensidade da
  luz (só aceita número de 1 a 100), horário da automação (tem que ser um
  HH:MM que existe de verdade), e-mail e senha do login.
- **A maquete 3D não tem regra de controle própria.** Um clique nela cai
  no mesmo fluxo de permissão que os cards já usavam — a diferença é só a
  interface, a lógica por trás é idêntica. O quadro de "poll" (consulta
  periódica) é o que deixa a maquete atualizada quando algo muda por fora
  dela — uma automação disparando, ou alguém mexendo em outra aba.
