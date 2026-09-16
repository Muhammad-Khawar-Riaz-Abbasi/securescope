from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import ActivityEvent, DeliveryRoute, FoodListing, Organization, Reservation, RouteStop

async def seed_demo(session: AsyncSession):
    if await session.scalar(select(Organization.id).limit(1)):
        return
    now = datetime.now(timezone.utc)
    donor = Organization(name="Juniper & Rye", kind="donor", description="Seasonal neighborhood kitchen", address="18 Market Street", city="Portland", contact_email="hello@juniperry.example", is_verified=True)
    grocer = Organization(name="Northstar Grocers", kind="donor", description="Community-first grocery partner", address="240 Alberta Ave", city="Portland", contact_email="community@northstar.example", is_verified=True)
    charity = Organization(name="Rose City Pantry", kind="charity", description="Fresh food for 12 neighborhood shelters", address="90 SE 8th Ave", city="Portland", contact_email="intake@rosecity.example", is_verified=True)
    shelter = Organization(name="Bridgeway Shelter", kind="charity", description="Low-barrier shelter and meal service", address="112 Burnside St", city="Portland", contact_email="meals@bridgeway.example", is_verified=True)
    session.add_all([donor, grocer, charity, shelter]); await session.flush()
    listings = [
      FoodListing(organization_id=donor.id, title="Herb roasted vegetable bowls", description="Ready-to-eat bowls from today's service.", category="Prepared meals", quantity=80, unit="portions", dietary_tags="vegetarian,vegan", allergens="sesame", pickup_start=now+timedelta(hours=2), pickup_end=now+timedelta(hours=5), address=donor.address, city=donor.city, meals_estimate=80),
      FoodListing(organization_id=grocer.id, title="Bakery surplus bundle", description="Fresh bread and pastries from the morning bake.", category="Bakery", quantity=45, unit="items", dietary_tags="vegetarian", allergens="wheat,milk,egg", pickup_start=now+timedelta(hours=4), pickup_end=now+timedelta(hours=8), address=grocer.address, city=grocer.city, meals_estimate=45),
      FoodListing(organization_id=donor.id, title="Seasonal soup & sourdough", description="Twenty liters of tomato-lentil soup with loaves.", category="Prepared meals", quantity=30, unit="servings", dietary_tags="vegan", allergens="wheat", pickup_start=now-timedelta(days=1), pickup_end=now+timedelta(hours=1), address=donor.address, city=donor.city, status="completed", meals_estimate=30),
    ]
    session.add_all(listings); await session.flush()
    route = DeliveryRoute(name="Eastside evening loop", scheduled_for=now+timedelta(days=1, hours=2), status="open", distance_km=12.4, notes="Two stops, insulated bags recommended")
    session.add(route); await session.flush()
    session.add(RouteStop(route_id=route.id, listing_id=listings[0].id, destination_name=charity.name, destination_address=charity.address, stop_order=1))
    session.add(Reservation(listing_id=listings[2].id, charity_id=shelter.id, quantity=30, status="completed", note="Delivered to evening meal service"))
    session.add(ActivityEvent(actor_name="HarvestLink", action="seeded_demo", entity_type="system", entity_id="demo", detail="Demo workspace initialized"))
    await session.commit()
