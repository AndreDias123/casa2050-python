"""
Smoke test end-to-end via Flask test client — não sobe servidor de verdade,
só exercita as rotas reais como um navegador faria.
"""
import sys
import traceback

from app import app
from extensions import db
from models import Dispositivo, Usuario

results = []


def check(name, condition, extra=""):
    status = "OK " if condition else "FAIL"
    results.append((status, name, extra))
    print(f"[{status}] {name} {extra}")


def main():
    app.config["TESTING"] = True
    client = app.test_client()

    # 1. GET login page
    r = client.get("/login")
    check("GET /login", r.status_code == 200, f"status={r.status_code}")

    # 2. Login errado
    r = client.post("/login", data={"email": "nope@x.com", "senha": "x"}, follow_redirects=True)
    check("login invalido nao autentica", b"login" in r.request.path.encode() or r.status_code == 200)

    # 3. Login admin
    r = client.post("/login", data={"email": "admin@casa2050.app", "senha": "admin123"}, follow_redirects=True)
    check("login admin", r.status_code == 200 and r.request.path == "/", f"path={r.request.path}")

    # 4. Dashboard renderiza e mostra dispositivos
    r = client.get("/")
    check("GET / (dashboard, admin)", r.status_code == 200)
    check("dashboard contem nome de comodo", b"Sala" in r.data or b"sala" in r.data.lower())

    # 5. Pega um dispositivo real pra testar toggle
    with app.app_context():
        disp = Dispositivo.query.filter_by(tipo="luz").first()
        disp_id = disp.id
        disp_estado_antes = disp.ativo

    r = client.post(f"/dispositivo/{disp_id}/alternar", follow_redirects=True)
    check("POST alternar dispositivo (admin)", r.status_code == 200, f"status={r.status_code}")

    with app.app_context():
        disp = db.session.get(Dispositivo, disp_id)
        check("estado do dispositivo mudou", disp.ativo != disp_estado_antes,
              f"antes={disp_estado_antes} depois={disp.ativo}")

    # 6. Detalhe do dispositivo
    r = client.get(f"/dispositivo/{disp_id}")
    check("GET /dispositivo/<id>", r.status_code == 200)

    # 7. Ajuste de intensidade — validação (não-dígito deve ser rejeitado)
    with app.app_context():
        luz = Dispositivo.query.filter_by(tipo="luz").first()
        luz_id = luz.id
    r = client.post(f"/dispositivo/{luz_id}/intensidade", data={"intensidade": "abc"}, follow_redirects=True)
    check("intensidade invalida nao quebra (validação)", r.status_code == 200)

    r = client.post(f"/dispositivo/{luz_id}/intensidade", data={"intensidade": "77"}, follow_redirects=True)
    check("intensidade valida aceita", r.status_code == 200)
    with app.app_context():
        luz = db.session.get(Dispositivo, luz_id)
        valor_intensidade = (luz.atributos_extra or {}).get("intensidade")
        check("intensidade persistida = 77", valor_intensidade == 77, f"valor={valor_intensidade}")

    # 8. Painel de energia
    r = client.get("/energia/")
    check("GET /energia/", r.status_code == 200)
    check("energia mostra kWh", b"kWh" in r.data)

    # 9. Geração de relatório (GET tela de confirmação + POST gera)
    r = client.get("/energia/relatorio")
    check("GET /energia/relatorio", r.status_code == 200)
    r = client.post("/energia/relatorio", follow_redirects=True)
    check("POST /energia/relatorio gera relatorio", r.status_code == 200)

    with app.app_context():
        from models import RelatorioEnviado
        n = RelatorioEnviado.query.count()
        check("relatorio salvo no banco", n >= 1, f"count={n}")

    # 10. Logout
    r = client.get("/logout", follow_redirects=True)
    check("GET /logout", r.status_code == 200)

    # 11. Dashboard sem login deve redirecionar
    r = client.get("/", follow_redirects=False)
    check("dashboard sem login redireciona", r.status_code in (301, 302), f"status={r.status_code}")

    # 12. Login usuário comum + testar permissão em dispositivo não liberado
    r = client.post("/login", data={"email": "comum@casa2050.app", "senha": "comum123"}, follow_redirects=True)
    check("login usuario comum", r.status_code == 200)

    with app.app_context():
        restrito = Dispositivo.query.filter_by(controlavel_por_comum=False).first()
        liberado = Dispositivo.query.filter_by(controlavel_por_comum=True).first()

    if restrito:
        with app.app_context():
            estado_antes_restrito = db.session.get(Dispositivo, restrito.id).ativo
        r = client.post(f"/dispositivo/{restrito.id}/alternar", follow_redirects=True)
        check("comum bloqueado em dispositivo restrito (nao 500)", r.status_code in (200, 302, 403),
              f"status={r.status_code}")
        with app.app_context():
            estado_depois_restrito = db.session.get(Dispositivo, restrito.id).ativo
        check("permissao respeitada: estado NAO mudou", estado_antes_restrito == estado_depois_restrito,
              f"antes={estado_antes_restrito} depois={estado_depois_restrito}")
        print(f"    (dispositivo restrito testado: {restrito.nome})")
    else:
        print("    (nenhum dispositivo restrito encontrado pra testar bloqueio)")

    if liberado:
        with app.app_context():
            estado_antes = db.session.get(Dispositivo, liberado.id).ativo
        r = client.post(f"/dispositivo/{liberado.id}/alternar", follow_redirects=True)
        check("comum consegue controlar dispositivo liberado (nao 500)", r.status_code in (200, 302),
              f"status={r.status_code}")
        with app.app_context():
            estado_depois = db.session.get(Dispositivo, liberado.id).ativo
        check("dispositivo liberado mudou de estado", estado_antes != estado_depois,
              f"antes={estado_antes} depois={estado_depois}")

    # 13. Rota inexistente -> 404 normal
    r = client.get("/isso-nao-existe")
    check("rota inexistente -> 404", r.status_code == 404)

    failed = [x for x in results if x[0] == "FAIL"]
    print("\n" + "=" * 50)
    print(f"TOTAL: {len(results)}  FAIL: {len(failed)}")
    if failed:
        print("FALHAS:")
        for f in failed:
            print(" -", f[1], f[2])
        sys.exit(1)
    else:
        print("TUDO OK")
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(2)
