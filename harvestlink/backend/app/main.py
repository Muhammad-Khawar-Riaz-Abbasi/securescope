import logging
from uuid import uuid4
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from .config import get_settings
from .db import get_session, init_db, SessionLocal
from .models import ActivityEvent, DeliveryRoute, FoodListing, Organization, Reservation, RouteStop
from .schemas import *
from .seed import seed_demo
from .services import MatchingProvider, calculate_impact, record_activity

settings = get_settings(); logger = logging.getLogger("harvestlink")
app = FastAPI(title="HarvestLink API", version="1.0.0", description="Surplus food rescue coordination API")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))[:80]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

async def protect(request: Request, x_api_key: str | None = Header(default=None)):
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

def listing_out(item: FoodListing) -> ListingOut:
    return ListingOut(id=item.id, organization_id=item.organization_id, title=item.title, description=item.description, category=item.category, quantity=item.quantity, unit=item.unit, dietary_tags=[x for x in item.dietary_tags.split(",") if x], allergens=[x for x in item.allergens.split(",") if x], pickup_start=item.pickup_start, pickup_end=item.pickup_end, address=item.address, city=item.city, status=item.status, meals_estimate=item.meals_estimate, organization_name=item.organization.name if item.organization else None, created_at=item.created_at)

@app.on_event("startup")
async def startup():
    await init_db()
    if settings.seed_demo:
        async with SessionLocal() as session: await seed_demo(session)

@app.get("/health", response_model=HealthOut)
async def health(request: Request): return {"status": "ok", "environment": settings.environment, "request_id": request.state.request_id}

@app.get("/api/v1/organizations", response_model=list[OrganizationOut], dependencies=[Depends(protect)])
async def organizations(session: AsyncSession = Depends(get_session)):
    return list((await session.execute(select(Organization).order_by(Organization.name))).scalars().all())

@app.post("/api/v1/organizations", response_model=OrganizationOut, status_code=201, dependencies=[Depends(protect)])
async def create_organization(payload: OrganizationCreate, session: AsyncSession = Depends(get_session)):
    item = Organization(**payload.model_dump()); session.add(item); await session.flush(); await record_activity(session, "Workspace admin", "created", "organization", item.id, item.name); await session.commit(); await session.refresh(item); return item

@app.get("/api/v1/listings", response_model=list[ListingOut], dependencies=[Depends(protect)])
async def listings(status_filter: str | None = Query(default=None, alias="status"), city: str | None = None, category: str | None = None, session: AsyncSession = Depends(get_session)):
    if status_filter == "available":
        items = await MatchingProvider().rank(session, city, category)
    elif status_filter:
        query = select(FoodListing).where(FoodListing.status == status_filter)
        if city: query = query.where(FoodListing.city.ilike(f"%{city}%"))
        if category: query = query.where(FoodListing.category.ilike(f"%{category}%"))
        items = list((await session.execute(query.order_by(FoodListing.pickup_end.asc()))).scalars().all())
    else:
        all_result = await session.execute(select(FoodListing).order_by(FoodListing.pickup_end.asc()))
        items = list(all_result.scalars().all())
    for item in items: await session.refresh(item, ["organization"])
    return [listing_out(item) for item in items]

@app.get("/api/v1/listings/{listing_id}", response_model=ListingOut, dependencies=[Depends(protect)])
async def listing_detail(listing_id: str, session: AsyncSession = Depends(get_session)):
    item = await session.get(FoodListing, listing_id)
    if not item: raise HTTPException(404, "Listing not found")
    await session.refresh(item, ["organization"]); return listing_out(item)

@app.post("/api/v1/listings", response_model=ListingOut, status_code=201, dependencies=[Depends(protect)])
async def create_listing(payload: ListingCreate, session: AsyncSession = Depends(get_session)):
    if not await session.get(Organization, payload.organization_id): raise HTTPException(404, "Organization not found")
    data = payload.model_dump(); data["dietary_tags"] = ",".join(data.pop("dietary_tags")); data["allergens"] = ",".join(data.pop("allergens")); data["meals_estimate"] = payload.quantity if payload.unit in {"meals", "portions", "servings"} else max(1, payload.quantity // 2)
    item = FoodListing(**data); session.add(item); await session.flush(); await record_activity(session, "Workspace admin", "created", "listing", item.id, item.title); await session.commit(); await session.refresh(item, ["organization"]); return listing_out(item)

@app.post("/api/v1/reservations", response_model=ReservationOut, status_code=201, dependencies=[Depends(protect)])
async def reserve(payload: ReservationCreate, session: AsyncSession = Depends(get_session)):
    listing = await session.get(FoodListing, payload.listing_id)
    charity = await session.get(Organization, payload.charity_id)
    if not listing or not charity: raise HTTPException(404, "Listing or charity not found")
    if charity.kind != "charity": raise HTTPException(400, "Reservations require a charity organization")
    if listing.status != "available": raise HTTPException(409, "Listing is no longer available")
    if payload.quantity > listing.quantity: raise HTTPException(400, "Requested quantity exceeds listing")
    duplicate = await session.scalar(select(Reservation).where(Reservation.listing_id == listing.id, Reservation.charity_id == charity.id, Reservation.status.in_(["reserved", "confirmed"])))
    if duplicate: raise HTTPException(409, "This charity already has an active reservation")
    item = Reservation(**payload.model_dump()); session.add(item); listing.status = "reserved"; await session.flush(); await record_activity(session, charity.name, "reserved", "listing", listing.id, f"{payload.quantity} {listing.unit}"); await session.commit(); await session.refresh(item); return item

@app.get("/api/v1/reservations", response_model=list[ReservationOut], dependencies=[Depends(protect)])
async def reservations(session: AsyncSession = Depends(get_session)):
    return list((await session.execute(select(Reservation).order_by(desc(Reservation.created_at)))).scalars().all())

@app.get("/api/v1/routes", response_model=list[RouteOut], dependencies=[Depends(protect)])
async def routes(session: AsyncSession = Depends(get_session)):
    items = list((await session.execute(select(DeliveryRoute).order_by(DeliveryRoute.scheduled_for))).scalars().all())
    for item in items: await session.refresh(item, ["stops"])
    return items

@app.post("/api/v1/routes", response_model=RouteOut, status_code=201, dependencies=[Depends(protect)])
async def create_route(payload: RouteCreate, session: AsyncSession = Depends(get_session)):
    item = DeliveryRoute(**payload.model_dump()); session.add(item); await session.flush(); await record_activity(session, "Dispatcher", "created", "route", item.id, item.name); await session.commit(); await session.refresh(item, ["stops"]); return item

@app.post("/api/v1/routes/{route_id}/claim", response_model=RouteOut, dependencies=[Depends(protect)])
async def claim_route(route_id: str, payload: RouteClaim, session: AsyncSession = Depends(get_session)):
    item = await session.get(DeliveryRoute, route_id)
    if not item: raise HTTPException(404, "Route not found")
    if item.status not in {"open", "claimed"}: raise HTTPException(409, "Route cannot be claimed in its current state")
    if item.volunteer_email and item.volunteer_email != str(payload.volunteer_email): raise HTTPException(409, "Route is already claimed")
    item.volunteer_name = payload.volunteer_name; item.volunteer_email = str(payload.volunteer_email); item.status = "claimed"; await record_activity(session, payload.volunteer_name, "claimed", "route", item.id, item.name); await session.commit(); await session.refresh(item, ["stops"]); return item

@app.post("/api/v1/routes/{route_id}/stops", response_model=StopOut, status_code=201, dependencies=[Depends(protect)])
async def add_stop(route_id: str, payload: RouteStopCreate, session: AsyncSession = Depends(get_session)):
    if not await session.get(DeliveryRoute, route_id) or not await session.get(FoodListing, payload.listing_id): raise HTTPException(404, "Route or listing not found")
    stop = RouteStop(route_id=route_id, **payload.model_dump()); session.add(stop); await session.commit(); await session.refresh(stop); return stop

@app.get("/api/v1/impact", response_model=ImpactOut, dependencies=[Depends(protect)])
async def impact(session: AsyncSession = Depends(get_session)): return await calculate_impact(session)

@app.get("/api/v1/activity", response_model=list[ActivityOut], dependencies=[Depends(protect)])
async def activity(limit: int = Query(50, ge=1, le=100), session: AsyncSession = Depends(get_session)):
    return list((await session.execute(select(ActivityEvent).order_by(desc(ActivityEvent.created_at)).limit(limit))).scalars().all())
