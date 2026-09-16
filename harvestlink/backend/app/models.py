from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

def new_id() -> str:
    return str(uuid4())

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False)

class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    address: Mapped[str] = mapped_column(String(240), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    listings = relationship("FoodListing", back_populates="organization")
    members = relationship("Member", back_populates="organization")

class Member(TimestampMixin, Base):
    __tablename__ = "members"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="member")
    organization = relationship("Organization", back_populates="members")

class FoodListing(TimestampMixin, Base):
    __tablename__ = "food_listings"
    __table_args__ = (Index("ix_food_listings_status_pickup", "status", "pickup_end"), Index("ix_food_listings_org", "organization_id"), CheckConstraint("quantity > 0", name="ck_listing_quantity_positive"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False, default="meals")
    dietary_tags: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    allergens: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    pickup_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pickup_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    address: Mapped[str] = mapped_column(String(240), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="available", nullable=False)
    meals_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    organization = relationship("Organization", back_populates="listings")
    reservations = relationship("Reservation", back_populates="listing")
    stops = relationship("RouteStop", back_populates="listing")

class Reservation(TimestampMixin, Base):
    __tablename__ = "reservations"
    __table_args__ = (Index("ix_reservations_listing_status", "listing_id", "status"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    listing_id: Mapped[str] = mapped_column(ForeignKey("food_listings.id", ondelete="CASCADE"), nullable=False)
    charity_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="reserved", nullable=False)
    note: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    listing = relationship("FoodListing", back_populates="reservations")
    charity = relationship("Organization", foreign_keys=[charity_id])

class DeliveryRoute(TimestampMixin, Base):
    __tablename__ = "delivery_routes"
    __table_args__ = (Index("ix_routes_status", "status"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    volunteer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    volunteer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    stops = relationship("RouteStop", back_populates="route", cascade="all, delete-orphan")

class RouteStop(TimestampMixin, Base):
    __tablename__ = "route_stops"
    __table_args__ = (Index("ix_route_stops_route_order", "route_id", "stop_order"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    route_id: Mapped[str] = mapped_column(ForeignKey("delivery_routes.id", ondelete="CASCADE"), nullable=False)
    listing_id: Mapped[str] = mapped_column(ForeignKey("food_listings.id", ondelete="CASCADE"), nullable=False)
    destination_name: Mapped[str] = mapped_column(String(140), nullable=False)
    destination_address: Mapped[str] = mapped_column(String(240), nullable=False)
    stop_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    route = relationship("DeliveryRoute", back_populates="stops")
    listing = relationship("FoodListing", back_populates="stops")

class ActivityEvent(Base):
    __tablename__ = "activity_events"
    __table_args__ = (Index("ix_activity_created", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    detail: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
