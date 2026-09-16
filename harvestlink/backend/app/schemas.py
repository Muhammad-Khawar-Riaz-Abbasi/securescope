from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class OrganizationBase(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    kind: str = Field(pattern="^(donor|charity|partner)$")
    description: str = Field(default="", max_length=1000)
    address: str = Field(min_length=5, max_length=240)
    city: str = Field(min_length=2, max_length=80)
    contact_email: EmailStr
    is_verified: bool = False
class OrganizationCreate(OrganizationBase): pass
class OrganizationOut(OrganizationBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime

class ListingCreate(BaseModel):
    organization_id: str
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=2000)
    category: str = Field(min_length=2, max_length=40)
    quantity: int = Field(gt=0, le=100000)
    unit: str = Field(default="meals", max_length=30)
    dietary_tags: list[str] = Field(default_factory=list, max_length=12)
    allergens: list[str] = Field(default_factory=list, max_length=12)
    pickup_start: datetime
    pickup_end: datetime
    address: str = Field(min_length=5, max_length=240)
    city: str = Field(min_length=2, max_length=80)
    @field_validator("pickup_end")
    @classmethod
    def after_start(cls, value, info):
        start = info.data.get("pickup_start")
        if start and value <= start:
            raise ValueError("pickup_end must be after pickup_start")
        return value
class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; organization_id: str; title: str; description: str; category: str; quantity: int; unit: str
    dietary_tags: list[str]; allergens: list[str]; pickup_start: datetime; pickup_end: datetime; address: str
    city: str; status: str; meals_estimate: int; organization_name: str | None = None; created_at: datetime

class ReservationCreate(BaseModel):
    listing_id: str
    charity_id: str
    quantity: int = Field(gt=0, le=100000)
    note: str = Field(default="", max_length=500)
class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; listing_id: str; charity_id: str; quantity: int; status: str; note: str; created_at: datetime

class RouteCreate(BaseModel):
    name: str = Field(min_length=3, max_length=140)
    scheduled_for: datetime
    distance_km: float = Field(ge=0, le=1000)
    notes: str = Field(default="", max_length=1000)
class RouteClaim(BaseModel):
    volunteer_name: str = Field(min_length=2, max_length=120)
    volunteer_email: EmailStr
class RouteStopCreate(BaseModel):
    listing_id: str
    destination_name: str = Field(min_length=2, max_length=140)
    destination_address: str = Field(min_length=5, max_length=240)
    stop_order: int = Field(ge=1, le=100)
class StopOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; listing_id: str; destination_name: str; destination_address: str; stop_order: int; status: str
class RouteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; name: str; volunteer_name: str | None; volunteer_email: str | None; scheduled_for: datetime
    status: str; distance_km: float; notes: str; stops: list[StopOut] = []; created_at: datetime

class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; actor_name: str; action: str; entity_type: str; entity_id: str; detail: str; created_at: datetime
class ImpactOut(BaseModel):
    meals_rescued: int; co2_saved_kg: float; water_saved_l: float; listings_completed: int; active_listings: int
class HealthOut(BaseModel): status: str; environment: str; request_id: str
