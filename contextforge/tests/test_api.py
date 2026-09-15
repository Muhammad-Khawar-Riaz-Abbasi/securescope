import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(db_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    with TestClient(app) as test_client:
        yield test_client


def test_health_and_vertical_slice(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    tenant = client.post("/v1/tenants", json={"name": "Acme"}).json()
    project = client.post(
        "/v1/projects", json={"tenant_id": tenant["id"], "name": "Checkout"}
    ).json()
    incident = client.post(
        "/v1/incidents",
        json={
            "project_id": project["id"],
            "title": "Latency",
            "description": "Checkout latency increased after deploy.",
        },
    ).json()
    document = client.post(
        f"/v1/projects/{project['id']}/documents",
        json={
            "title": "Runbook",
            "content": "Rollback the checkout deployment after latency increases.",
        },
    ).json()
    duplicate = client.post(
        f"/v1/projects/{project['id']}/documents",
        json={
            "title": "Same content",
            "content": "Rollback the checkout deployment after latency increases.",
        },
    ).json()
    assert document["duplicate"] is False
    assert duplicate["duplicate"] is True

    answer = client.post(
        f"/v1/incidents/{incident['id']}/ask",
        json={"question": "What should we do after latency increases?"},
    )
    assert answer.status_code == 200
    body = answer.json()
    assert body["citations"]
    assert 0 <= body["confidence"] <= 1


def test_validation_and_request_id(client):
    response = client.post(
        "/v1/tenants", json={"name": ""}, headers={"X-Request-ID": "test-request"}
    )
    assert response.status_code == 422
    assert response.headers["X-Request-ID"] == "test-request"


@pytest.mark.parametrize(
    "path", ["/v1/projects/not-a-uuid/documents", "/v1/incidents/not-a-uuid/ask"]
)
def test_invalid_paths_are_rejected(client, path):
    response = client.post(path, json={"question": "why", "title": "x", "content": "y"})
    assert response.status_code == 422
