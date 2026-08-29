from flask import Flask
from flask_login import current_user
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
from markupsafe import Markup

from config import Config
from extensions import db, login_manager
from models import Usuario
from services.agendador import iniciar_agendador

csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from auth import bp as auth_bp
    from main import bp as main_bp
    from energia import bp as energia_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(energia_bp)

    @login_manager.user_loader
    def carregar_usuario(usuario_id):
        return db.session.get(Usuario, int(usuario_id))

    @app.context_processor
    def injetar_usuario():
        return {"usuario_logado": current_user}

    @app.template_global()
    def csrf_field():
        return Markup(f'<input type="hidden" name="csrf_token" value="{generate_csrf()}">')

    iniciar_agendador(app)

    return app


app = create_app()

if __name__ == "__main__":
    # debug=True só para desenvolvimento local — desligue em produção.
    app.run(debug=True, port=5000)
