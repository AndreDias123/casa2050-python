"""
Modelagem de dados da Casa 2050.

Mapeamento das entidades para o SQLAlchemy usando Single Table Inheritance
para `Dispositivo`: uma única tabela `dispositivos`, discriminada pela coluna
`tipo`, com uma subclasse Python por tipo de dispositivo (Luz, Porta, Janela,
Camera, TV, Eletrodomestico, RoboAspirador, ArCondicionado). Isso é o que
materializa herança e polimorfismo no banco: cada subclasse sobrescreve
`ligar()`/`desligar()`/`status()` do seu próprio jeito, mas todo o resto do
sistema (rotas, templates) trabalha só com a interface comum `Dispositivo`.
"""
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


def agora():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Usuário e perfis
# ---------------------------------------------------------------------------
class Usuario(db.Model, UserMixin):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    # 'administrador' (mora na casa, controla tudo) ou 'usuario_comum' (acesso limitado)
    perfil = db.Column(db.String(20), nullable=False, default="usuario_comum")
    criado_em = db.Column(db.DateTime, default=agora)

    automacoes = db.relationship("Automacao", back_populates="criado_por", cascade="all, delete-orphan")
    relatorios = db.relationship("RelatorioEnviado", back_populates="usuario", cascade="all, delete-orphan")

    def set_senha(self, senha_plana):
        self.senha_hash = generate_password_hash(senha_plana)

    def checar_senha(self, senha_plana):
        return check_password_hash(self.senha_hash, senha_plana)

    @property
    def is_admin(self):
        return self.perfil == "administrador"

    def __repr__(self):
        return f"<Usuario {self.email} ({self.perfil})>"


# ---------------------------------------------------------------------------
# Cômodo
# ---------------------------------------------------------------------------
class Comodo(db.Model):
    __tablename__ = "comodos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(60), nullable=False, unique=True)

    dispositivos = db.relationship("Dispositivo", back_populates="comodo", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Comodo {self.nome}>"


# ---------------------------------------------------------------------------
# Dispositivo (classe base) + subclasses por tipo (Single Table Inheritance)
# ---------------------------------------------------------------------------
class Dispositivo(db.Model):
    __tablename__ = "dispositivos"

    id = db.Column(db.Integer, primary_key=True)
    comodo_id = db.Column(db.Integer, db.ForeignKey("comodos.id"), nullable=False)
    nome = db.Column(db.String(80), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)  # discriminador da herança

    # Estado genérico "ativo/inativo": cada subclasse decide o que isso
    # significa na prática (uma Luz ligada, uma Porta destrancada, uma
    # Janela aberta...) — isso é o polimorfismo pedido no projeto.
    ativo = db.Column(db.Boolean, nullable=False, default=False)

    potencia_watts = db.Column(db.Integer, nullable=False, default=0)
    controlavel_por_comum = db.Column(db.Boolean, nullable=False, default=False)
    atributos_extra = db.Column(db.JSON, nullable=False, default=dict)

    comodo = db.relationship("Comodo", back_populates="dispositivos")
    registros = db.relationship(
        "RegistroUso", back_populates="dispositivo", cascade="all, delete-orphan",
        order_by="RegistroUso.timestamp",
    )

    __mapper_args__ = {"polymorphic_identity": "dispositivo", "polymorphic_on": tipo}

    # --- comportamento comum, sobrescrito pelas subclasses quando faz sentido ---
    def ligar(self, usuario=None):
        self.ativo = True
        self._registrar(usuario, "ligou")

    def desligar(self, usuario=None):
        self.ativo = False
        self._registrar(usuario, "desligou")

    def alternar(self, usuario=None):
        self.desligar(usuario) if self.ativo else self.ligar(usuario)

    def status(self):
        return "Ligado" if self.ativo else "Desligado"

    def icone(self):
        return "generico"

    def pode_controlar(self, usuario):
        """Regra de permissão: Administrador sempre pode; Usuário Comum só
        se o dispositivo estiver marcado como controlável por ele."""
        return bool(usuario) and (usuario.is_admin or self.controlavel_por_comum)

    def _registrar(self, usuario, evento, valor=None):
        db.session.add(RegistroUso(
            dispositivo=self,
            usuario_id=usuario.id if usuario else None,
            evento=evento,
            valor=valor,
        ))

    def __repr__(self):
        return f"<{type(self).__name__} {self.nome!r}>"


class Luz(Dispositivo):
    __mapper_args__ = {"polymorphic_identity": "luz"}

    def status(self):
        if not self.ativo:
            return "Desligada"
        intensidade = (self.atributos_extra or {}).get("intensidade", 100)
        return f"Ligada · {intensidade}%"

    def ajustar_intensidade(self, valor, usuario=None):
        valor = max(1, min(100, int(valor)))
        self.atributos_extra = {**(self.atributos_extra or {}), "intensidade": valor}
        self._registrar(usuario, "ajustou", {"intensidade": valor})

    def icone(self):
        return "luz"


class Porta(Dispositivo):
    __mapper_args__ = {"polymorphic_identity": "porta"}

    def status(self):
        return "Destrancada" if self.ativo else "Trancada"

    def icone(self):
        return "porta"


class Janela(Dispositivo):
    __mapper_args__ = {"polymorphic_identity": "janela"}

    def status(self):
        return "Aberta" if self.ativo else "Fechada"

    def icone(self):
        return "janela"


class Camera(Dispositivo):
    __mapper_args__ = {"polymorphic_identity": "camera"}

    def status(self):
        return "Gravando" if self.ativo else "Desligada"

    def icone(self):
        return "camera"


class TV(Dispositivo):
    __mapper_args__ = {"polymorphic_identity": "tv"}

    def icone(self):
        return "tv"


class Eletrodomestico(Dispositivo):
    __mapper_args__ = {"polymorphic_identity": "eletrodomestico"}

    def status(self):
        return "Sempre ligada" if self.ativo else "Desligada"

    def icone(self):
        return "eletrodomestico"


class RoboAspirador(Dispositivo):
    __mapper_args__ = {"polymorphic_identity": "robo_aspirador"}

    def status(self):
        bateria = (self.atributos_extra or {}).get("bateria", 100)
        return f"Limpando · {bateria}%" if self.ativo else f"Na base · {bateria}%"

    def icone(self):
        return "robo"


class ArCondicionado(Dispositivo):
    __mapper_args__ = {"polymorphic_identity": "ar_condicionado"}

    def status(self):
        if not self.ativo:
            return "Desligado"
        temp = (self.atributos_extra or {}).get("temperatura", 22)
        return f"Ligado · {temp}°C"

    def icone(self):
        return "ac"


# ---------------------------------------------------------------------------
# Histórico de uso — matéria-prima do cálculo de consumo de energia
# ---------------------------------------------------------------------------
class RegistroUso(db.Model):
    __tablename__ = "registros_uso"

    id = db.Column(db.Integer, primary_key=True)
    dispositivo_id = db.Column(db.Integer, db.ForeignKey("dispositivos.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)  # nulo = automação
    evento = db.Column(db.String(20), nullable=False)  # 'ligou' | 'desligou' | 'ajustou'
    valor = db.Column(db.JSON, nullable=True)
    timestamp = db.Column(db.DateTime, default=agora, nullable=False)

    dispositivo = db.relationship("Dispositivo", back_populates="registros")
    usuario = db.relationship("Usuario")


# ---------------------------------------------------------------------------
# Tarifa de energia
# ---------------------------------------------------------------------------
class TarifaEnergia(db.Model):
    __tablename__ = "tarifas_energia"

    id = db.Column(db.Integer, primary_key=True)
    valor_kwh = db.Column(db.Float, nullable=False)
    vigente_desde = db.Column(db.DateTime, default=agora, nullable=False)
    vigente_ate = db.Column(db.DateTime, nullable=True)  # nulo = ainda vigente


# ---------------------------------------------------------------------------
# Automação (rotina) — ex.: "acender a luz do quarto às 18:30"
# ---------------------------------------------------------------------------
class Automacao(db.Model):
    __tablename__ = "automacoes"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    horario = db.Column(db.String(5), nullable=False)  # 'HH:MM'
    dias_semana = db.Column(db.String(40), nullable=False, default="todos")
    ativa = db.Column(db.Boolean, nullable=False, default=True)

    criado_por = db.relationship("Usuario", back_populates="automacoes")
    acoes = db.relationship("AutomacaoAcao", back_populates="automacao", cascade="all, delete-orphan")


class AutomacaoAcao(db.Model):
    """Uma automação pode disparar ações em vários dispositivos — por isso
    esta tabela de junção em vez de a automação apontar para um único
    dispositivo."""
    __tablename__ = "automacao_acoes"

    id = db.Column(db.Integer, primary_key=True)
    automacao_id = db.Column(db.Integer, db.ForeignKey("automacoes.id"), nullable=False)
    dispositivo_id = db.Column(db.Integer, db.ForeignKey("dispositivos.id"), nullable=False)
    acao = db.Column(db.String(20), nullable=False)  # 'ligar' | 'desligar'

    automacao = db.relationship("Automacao", back_populates="acoes")
    dispositivo = db.relationship("Dispositivo")


# ---------------------------------------------------------------------------
# Relatório de consumo enviado por e-mail (snapshot congelado)
# ---------------------------------------------------------------------------
class RelatorioEnviado(db.Model):
    __tablename__ = "relatorios_enviados"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    periodo_inicio = db.Column(db.DateTime, nullable=False)
    periodo_fim = db.Column(db.DateTime, nullable=False)
    kwh_total = db.Column(db.Float, nullable=False)
    custo_total = db.Column(db.Float, nullable=False)
    tarifa_usada = db.Column(db.Float, nullable=False)
    enviado_em = db.Column(db.DateTime, default=agora, nullable=False)
    enviado_de_verdade = db.Column(db.Boolean, nullable=False, default=False)

    usuario = db.relationship("Usuario", back_populates="relatorios")
