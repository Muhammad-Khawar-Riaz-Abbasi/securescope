import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.db import Base, engine
from app.config import get_settings

@pytest.fixture(autouse=True)
async def reset_db():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    from app.db import SessionLocal
    from app.seed import seed_demo
    async with SessionLocal() as session: await seed_demo(session)
    yield

@pytest.mark.asyncio
async def test_health_and_seeded_listings():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/health")).json()["status"] == "ok"
        response = await client.get("/api/v1/listings")
        assert response.status_code == 200
        assert len(response.json()) >= 3
        completed = await client.get("/api/v1/listings?status=completed")
        assert completed.status_code == 200
        assert completed.json()[0]["status"] == "completed"

@pytest.mark.asyncio
async def test_reservation_prevents_duplicate():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        listings = (await client.get("/api/v1/listings?status=available")).json()
        organizations = (await client.get("/api/v1/organizations")).json()
        charity = next(item for item in organizations if item["kind"] == "charity")
        payload = {"listing_id": listings[0]["id"], "charity_id": charity["id"], "quantity": 2}
        assert (await client.post("/api/v1/reservations", json=payload)).status_code == 201
        assert (await client.post("/api/v1/reservations", json=payload)).status_code == 409
