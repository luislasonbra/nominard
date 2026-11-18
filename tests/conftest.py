import os
import sys
import tempfile

import pytest

# Debe ejecutarse ANTES de importar app: usa una base de datos temporal.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = "sqlite:///" + _tmp.name
os.environ["SECRET_KEY"] = "clave-de-pruebas-de-mas-de-24-caracteres"
os.environ["ADMIN_EMAIL"] = "admin@test.local"
os.environ["ADMIN_PASSWORD"] = "admin1234"
os.environ.pop("APP_ENV", None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app  # noqa: E402


@pytest.fixture(scope="session")
def app():
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_client(client):
    r = client.post("/api/auth/login",
                    json={"email": "admin@test.local", "password": "admin1234"})
    assert r.status_code == 200
    return client
