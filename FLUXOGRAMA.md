# Fluxograma da aplicação

Fluxo completo do PULSE2050, das duas entradas do sistema (uma pessoa
usando a interface, e o agendador rodando sozinho em segundo plano) até os
efeitos finais no banco de dados.

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

## Como ler

- **Dois pontos de entrada de dados no `RegistroUso`:** uma pessoa
  interagindo pela UI (`usuario` preenchido) ou o agendador disparando uma
  automação sozinho (`usuario = None`) — os dois alimentam o mesmo cálculo
  de energia, sem caminho especial pra automação.
- **Toda ação de controle passa por uma checagem de permissão**
  (`Dispositivo.pode_controlar()`) antes de qualquer mudança de estado —
  aparece três vezes no fluxo (alternar dispositivo, alternar automação,
  mudar permissão) porque é a mesma regra aplicada em pontos diferentes.
- **Toda entrada de formulário é validada antes de tocar no banco** —
  intensidade (dígito 1-100), horário da automação (HH:MM válido),
  credenciais de login.
- **A Maquete 3D não tem lógica própria de controle** — um clique nela cai
  no mesmo `PermToggle` que os cards usam, então a regra de permissão e o
  `RegistroUso` gerado são idênticos, só a interface é diferente. O `POLL`
  em paralelo é o que permite a maquete refletir uma automação disparando
  sozinha (ou alguém mexendo em outra aba) sem precisar recarregar a
  página — ela lê o mesmo estado que qualquer um dos três `RegistroUso`
  do fluxo principal deixou no banco.
