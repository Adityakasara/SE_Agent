from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_api_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_api_list_repositories():
    response = client.get("/repositories")
    assert response.status_code == 200
    repos = response.json()["repositories"]
    assert any(r["repo_name"] == "demo_fastapi_app" for r in repos)


def test_api_create_and_approve_task():
    # 1. Create task
    create_res = client.post(
        "/tasks",
        json={
            "repository_name": "demo_fastapi_app",
            "task_description": "Fix the /users API returning HTTP 500 when email is missing.",
        },
    )
    assert create_res.status_code == 201
    task_id = create_res.json()["task_id"]
    assert task_id is not None

    # 2. Check task status
    status_res = client.get(f"/tasks/{task_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "AWAITING_APPROVAL"

    # 3. Check diff endpoint
    diff_res = client.get(f"/tasks/{task_id}/diff")
    assert diff_res.status_code == 200

    # 4. Check agent trace endpoint
    agents_res = client.get(f"/tasks/{task_id}/agents")
    assert agents_res.status_code == 200
    assert len(agents_res.json()["trace"]) > 0

    # 5. Approve task
    approve_res = client.post(
        f"/tasks/{task_id}/approve",
        json={"feedback": "Looks solid, proceed with merge."},
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "COMPLETED"
