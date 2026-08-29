"""
Popula o banco com dados de exemplo: cômodos, dispositivos (com potência
real em Watts), dois usuários (Administrador e Usuário Comum) e duas semanas
de histórico de uso sintético — para que o painel de energia mostre números
calculados de verdade pelo services/energia.py (incluindo a comparação com a
semana anterior e o alerta de consumo), não valores fixos.

Uso:
    python seed.py            # cria/recria o banco com dados de exemplo
"""
from datetime import datetime, timedelta, timezone

from app import create_app
from extensions import db
from models import (
    Usuario, Comodo, TarifaEnergia, RegistroUso, Automacao, AutomacaoAcao,
    Luz, Porta, Janela, Camera, TV, Eletrodomestico, RoboAspirador, ArCondicionado,
)


def _janela_diaria(dispositivo, hora_inicio, hora_fim, dias_atras_inicio=14, dias_atras_fim=1):
    """Gera pares ligou/desligou para os últimos N dias completos (sem contar hoje)."""
    agora = datetime.now(timezone.utc)
    for dias in range(dias_atras_inicio, dias_atras_fim - 1, -1):
        dia = (agora - timedelta(days=dias)).replace(hour=0, minute=0, second=0, microsecond=0)
        inicio = dia + timedelta(hours=hora_inicio)
        fim = dia + timedelta(hours=hora_fim)
        db.session.add(RegistroUso(dispositivo=dispositivo, evento="ligou", timestamp=inicio))
        db.session.add(RegistroUso(dispositivo=dispositivo, evento="desligou", timestamp=fim))


def _ligado_continuamente_ha(dispositivo, dias):
    inicio = datetime.now(timezone.utc) - timedelta(days=dias)
    db.session.add(RegistroUso(dispositivo=dispositivo, evento="ligou", timestamp=inicio))
    dispositivo.ativo = True


def _deixar_ligado_hoje_desde(dispositivo, hora_inicio):
    hoje = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    inicio = hoje + timedelta(hours=hora_inicio)
    if inicio <= datetime.now(timezone.utc):
        db.session.add(RegistroUso(dispositivo=dispositivo, evento="ligou", timestamp=inicio))
        dispositivo.ativo = True


def seed():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        # --- usuários ---
        admin = Usuario(nome="André", email="admin@pulse2050.app", perfil="administrador")
        admin.set_senha("admin123")
        comum = Usuario(nome="Visitante", email="comum@pulse2050.app", perfil="usuario_comum")
        comum.set_senha("comum123")
        db.session.add_all([admin, comum])

        # --- tarifa vigente ---
        db.session.add(TarifaEnergia(valor_kwh=0.92))

        # --- cômodos ---
        quarto = Comodo(nome="Quarto")
        sala = Comodo(nome="Sala")
        cozinha = Comodo(nome="Cozinha")
        garagem = Comodo(nome="Garagem")
        externa = Comodo(nome="Área Externa")
        db.session.add_all([quarto, sala, cozinha, garagem, externa])

        # --- dispositivos (nome, cômodo, potência em Watts, controlável por usuário comum) ---
        luz_quarto = Luz(nome="Luz do Quarto", comodo=quarto, potencia_watts=9, controlavel_por_comum=False)
        janela_quarto = Janela(nome="Janela do Quarto", comodo=quarto, potencia_watts=0, controlavel_por_comum=True)
        ac_quarto = ArCondicionado(nome="Ar-condicionado", comodo=quarto, potencia_watts=1200, controlavel_por_comum=False,
                                    atributos_extra={"temperatura": 22})

        luz_sala = Luz(nome="Luz da Sala", comodo=sala, potencia_watts=12, controlavel_por_comum=True)
        tv_sala = TV(nome="TV da Sala", comodo=sala, potencia_watts=120, controlavel_por_comum=True)
        camera_sala = Camera(nome="Câmera da Sala", comodo=sala, potencia_watts=5, controlavel_por_comum=False)

        luz_cozinha = Luz(nome="Luz da Cozinha", comodo=cozinha, potencia_watts=12, controlavel_por_comum=True)
        geladeira = Eletrodomestico(nome="Geladeira", comodo=cozinha, potencia_watts=150, controlavel_por_comum=False)
        robo = RoboAspirador(nome="Robô Aspirador", comodo=cozinha, potencia_watts=35, controlavel_por_comum=True,
                              atributos_extra={"bateria": 82})

        porta_garagem = Porta(nome="Porta da Garagem", comodo=garagem, potencia_watts=150, controlavel_por_comum=False)
        luz_garagem = Luz(nome="Luz da Garagem", comodo=garagem, potencia_watts=15, controlavel_por_comum=True)

        camera_externa = Camera(nome="Câmera Externa", comodo=externa, potencia_watts=6, controlavel_por_comum=False)
        luz_externa = Luz(nome="Luz Externa", comodo=externa, potencia_watts=20, controlavel_por_comum=False)

        dispositivos = [
            luz_quarto, janela_quarto, ac_quarto,
            luz_sala, tv_sala, camera_sala,
            luz_cozinha, geladeira, robo,
            porta_garagem, luz_garagem,
            camera_externa, luz_externa,
        ]
        db.session.add_all(dispositivos)
        db.session.flush()  # garante que cada dispositivo já tem id antes dos RegistroUso

        # --- duas semanas de histórico sintético: a mais antiga serve de base de
        # comparação (variação %, projeção) pro painel de energia; só o
        # ar-condicionado tem uma tendência real de alta na semana mais recente,
        # pra exercitar o alerta de consumo com um número plausível. ---
        _janela_diaria(luz_quarto, 18.5, 23.0)
        _janela_diaria(luz_sala, 18.0, 23.5)
        _janela_diaria(tv_sala, 19.0, 22.5)
        _janela_diaria(luz_cozinha, 18.0, 21.0)
        _janela_diaria(robo, 10.0, 10.75)
        _janela_diaria(luz_externa, 18.0, 30.0)  # liga ao anoitecer, apaga ao amanhecer

        # ar-condicionado: 7h/noite na semana anterior, 8,5h/noite na semana
        # atual (22h -> 06h/06h30 do dia seguinte) — cerca de +21%.
        _janela_diaria(ac_quarto, 22.0, 29.0, dias_atras_inicio=14, dias_atras_fim=8)
        _janela_diaria(ac_quarto, 22.0, 30.5, dias_atras_inicio=7, dias_atras_fim=1)

        _ligado_continuamente_ha(camera_sala, dias=14)
        _ligado_continuamente_ha(camera_externa, dias=14)
        _ligado_continuamente_ha(geladeira, dias=14)

        # alguns usos rápidos da porta da garagem nas duas semanas (motor liga por pouco tempo)
        agora = datetime.now(timezone.utc)
        for dias in (12, 9, 5, 2):
            momento = agora - timedelta(days=dias, hours=3)
            db.session.add(RegistroUso(dispositivo=porta_garagem, evento="ligou", timestamp=momento))
            db.session.add(RegistroUso(dispositivo=porta_garagem, evento="desligou",
                                        timestamp=momento + timedelta(minutes=1)))

        # --- automações de exemplo, já disparadas de verdade pelo agendador (services/agendador.py) ---
        acender_quarto = Automacao(nome="Acender à noite", horario="18:30", criado_por=admin)
        acender_quarto.acoes.append(AutomacaoAcao(dispositivo=luz_quarto, acao="ligar"))
        apagar_quarto = Automacao(nome="Apagar à noite", horario="23:00", criado_por=admin)
        apagar_quarto.acoes.append(AutomacaoAcao(dispositivo=luz_quarto, acao="desligar"))

        acender_externa = Automacao(nome="Acender ao anoitecer", horario="18:00", criado_por=admin)
        acender_externa.acoes.append(AutomacaoAcao(dispositivo=luz_externa, acao="ligar"))
        apagar_externa = Automacao(nome="Apagar ao amanhecer", horario="06:00", criado_por=admin)
        apagar_externa.acoes.append(AutomacaoAcao(dispositivo=luz_externa, acao="desligar"))

        db.session.add_all([acender_quarto, apagar_quarto, acender_externa, apagar_externa])

        # --- estado de "agora" (hoje), para bater com o que a equipe já desenhou no protótipo ---
        _deixar_ligado_hoje_desde(luz_quarto, 18.5)
        _deixar_ligado_hoje_desde(luz_sala, 18.0)
        _deixar_ligado_hoje_desde(tv_sala, 19.0)
        _deixar_ligado_hoje_desde(luz_externa, 18.0)
        janela_quarto.ativo = False       # fechada
        luz_cozinha.ativo = False         # desligada
        porta_garagem.ativo = False       # trancada
        luz_garagem.ativo = False         # desligada
        robo.ativo = False                # na base

        db.session.commit()

        print("Banco criado e populado em pulse2050.db")
        print("  Administrador: admin@pulse2050.app / admin123")
        print("  Usuário comum: comum@pulse2050.app / comum123")


if __name__ == "__main__":
    seed()
