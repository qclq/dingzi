from fastapi.testclient import TestClient

from app.main import app


def test_root_metadata() -> None:
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "dingzi-web-api"
