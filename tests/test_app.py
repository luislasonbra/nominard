from app import calcular_isr


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_home_carga(client):
    assert client.get("/").status_code == 200


def test_api_exige_sesion(client):
    assert client.get("/api/empleados").status_code == 401


def test_login_incorrecto(client):
    r = client.post("/api/auth/login",
                    json={"email": "admin@test.local", "password": "mala"})
    assert r.status_code == 401


def test_login_ok_y_cookie_session(client):
    r = client.post("/api/auth/login",
                    json={"email": "admin@test.local", "password": "admin1234"})
    assert r.status_code == 200
    # Firebase Hosting solo deja pasar la cookie "__session"
    assert "__session=" in r.headers.get("Set-Cookie", "")


def test_api_no_se_cachea(auth_client):
    r = auth_client.get("/api/departamentos")
    assert r.status_code == 200
    assert "no-store" in r.headers["Cache-Control"]


def test_crud_departamento(auth_client):
    r = auth_client.post("/api/departamentos",
                         json={"nombre": "Pruebas", "codigo": "tst"})
    assert r.status_code in (200, 201)
    lista = auth_client.get("/api/departamentos").get_json()
    assert any(d["nombre"] == "Pruebas" for d in lista)


def test_olvide_contrasena_no_expone_token_en_produccion(client, app):
    app.config["EXPOSE_RESET_TOKEN"] = False
    r = client.post("/api/auth/forgot-password", json={"email": "admin@test.local"})
    assert "reset_token" not in r.get_json()
    app.config["EXPOSE_RESET_TOKEN"] = True


def test_isr_escalas():
    assert calcular_isr(30000) == 0                       # 360,000 anual: exento
    assert calcular_isr(40000) == round((480000 - 416220) * 0.15 / 12, 2)


def test_registro_publico_cerrado_en_produccion(client, app):
    app.config["ALLOW_REGISTRATION"] = False
    r = client.post("/api/auth/register",
                    json={"nombre": "X", "email": "x@x.com", "password": "123456"})
    assert r.status_code == 403
    app.config["ALLOW_REGISTRATION"] = True
