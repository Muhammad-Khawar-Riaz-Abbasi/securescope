from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import ActivityEvent, FoodListing, Organization, Reservation

class MatchingProvider:
    """Deterministic matching seam; replaceable with a ranking provider later."""
    async def rank(self, session: AsyncSession, city: str | None = None, category: str | None = None):
        query = select(FoodListing).where(FoodListing.status == "available")
        if city: query = query.where(FoodListing.city.ilike(f"%{city}%"))
        if category: query = query.where(FoodListing.category.ilike(f"%{category}%"))
        result = await session.execute(query.order_by(FoodListing.pickup_end.asc()))
        return list(result.scalars().all())

class ImpactProvider:
    """Transparent local assumptions: one meal=0.8kg CO2 and 200L water."""
    co2_per_meal = 0.8
    water_per_meal = 200
    def calculate(self, meals: int) -> dict:
        return {"meals_rescued": meals, "co2_saved_kg": round(meals * self.co2_per_meal, 1), "water_saved_l": meals * self.water_per_meal}

async def record_activity(session: AsyncSession, actor: str, action: str, entity_type: str, entity_id: str, detail: str = ""):
    session.add(ActivityEvent(actor_name=actor, action=action, entity_type=entity_type, entity_id=entity_id, detail=detail))

async def calculate_impact(session: AsyncSession) -> dict:
    completed = await session.scalar(select(func.coalesce(func.sum(FoodListing.meals_estimate), 0)).where(FoodListing.status.in_(["reserved", "completed"])))
    active = await session.scalar(select(func.count()).select_from(FoodListing).where(FoodListing.status == "available"))
    completed_count = await session.scalar(select(func.count()).select_from(FoodListing).where(FoodListing.status.in_(["reserved", "completed"])))
    impact = ImpactProvider().calculate(int(completed or 0))
    return {**impact, "listings_completed": int(completed_count or 0), "active_listings": int(active or 0)}
