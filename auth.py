from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from models import Usuario

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    # Quem já está logado não precisa ver a tela de login de novo.
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        # Validação básica de formulário: campos vazios nem chegam a
        # consultar o banco.
        email = (request.form.get("email") or "").strip().lower()
        senha = request.form.get("senha") or ""

        if not email or not senha:
            flash("Preencha usuário e senha.", "erro")
            return render_template("login.html")

        # Mesma mensagem de erro tanto pra "e-mail não existe" quanto pra
        # "senha errada" — não vale dar pista de qual dos dois está certo.
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario is None or not usuario.checar_senha(senha):
            flash("Usuário ou senha inválidos.", "erro")
            return render_template("login.html")

        # login_user cria a sessão (Flask-Login); remember=True faz o Flask
        # gravar um cookie de longa duração, então a sessão sobrevive a
        # fechar o navegador (a checkbox "lembrar de mim" da tela).
        login_user(usuario, remember=bool(request.form.get("lembrar")))
        return redirect(url_for("main.dashboard"))

    return render_template("login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
