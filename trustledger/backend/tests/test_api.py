import io

import pytest


@pytest.mark.asyncio
async def test_vendor_upload_duplicate_and_detail(client):
    response = await client.post("/api/vendors", json={"name": "Acme Cloud", "owner": "Sam"})
    assert response.status_code == 201
    vendor_id = response.json()["id"]
    document = b"This contract has automatic renewal and a 30 day breach notification window."
    upload = await client.post(
        f"/api/vendors/{vendor_id}/documents",
        files={"file": ("acme-contract.txt", io.BytesIO(document), "text/plain")},
    )
    assert upload.status_code == 200
    assert upload.json()["findings_created"] == 2
    duplicate = await client.post(
        f"/api/vendors/{vendor_id}/documents",
        files={"file": ("copy.txt", io.BytesIO(document), "text/plain")},
    )
    assert duplicate.json()["duplicate"] is True
    detail = await client.get(f"/api/vendors/{vendor_id}")
    assert detail.status_code == 200
    assert detail.json()["document_count"] == 1
    assert detail.json()["risk_score"] < 100


@pytest.mark.asyncio
async def test_question_answer_has_citation(client):
    vendor_id = (await client.post("/api/vendors", json={"name": "Northstar"})).json()["id"]
    await client.post(
        f"/api/vendors/{vendor_id}/documents",
        files={
            "file": (
                "policy.txt",
                io.BytesIO(b"We maintain ISO 27001 certification and business continuity plans."),
                "text/plain",
            )
        },
    )
    response = await client.post(
        f"/api/vendors/{vendor_id}/ask",
        json={"question": "What certification does the vendor maintain?"},
    )
    assert response.status_code == 200
    assert response.json()["citations"]
    assert "ISO" in response.json()["answer"]
