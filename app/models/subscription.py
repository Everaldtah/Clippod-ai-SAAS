"""Subscription model for billing."""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Enum as SQLEnum, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class SubscriptionPlan(str, PyEnum):
    """Subscription plans."""
    FREE = "free"
    PRO = "pro"
    AGENCY = "agency"


class SubscriptionStatus(str, PyEnum):
    """Subscription status."""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    TRIALING = "trialing"


class Subscription(Base):
    """Subscription model for billing."""
    
    __tablename__ = "subscriptions"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Plan info
    plan: Mapped[SubscriptionPlan] = mapped_column(
        SQLEnum(SubscriptionPlan),
        default=SubscriptionPlan.FREE,
        nullable=False
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        SQLEnum(SubscriptionStatus),
        default=SubscriptionStatus.ACTIVE,
        nullable=False
    )
    
    # Stripe info
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    stripe_price_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Billing
    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Usage limits (based on plan)
    monthly_uploads_limit: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    monthly_renders_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    storage_gb_limit: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Current usage
    uploads_used_this_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    renders_used_this_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    storage_used_gb: Mapped[float] = mapped_column(default=0.0, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="subscription")
    
    def __repr__(self) -> str:
        return f"<Subscription {self.plan} - {self.status}>"
    
    def is_active(self) -> bool:
        """Check if subscription is active."""
        if self.plan == SubscriptionPlan.FREE:
            return True
        return self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]
    
    def can_upload(self) -> bool:
        """Check if user can upload more videos this month."""
        return self.uploads_used_this_month < self.monthly_uploads_limit
    
    def can_render(self) -> bool:
        """Check if user can render more clips this month."""
        return self.renders_used_this_month < self.monthly_renders_limit
    
    def get_uploads_remaining(self) -> int:
        """Get remaining uploads for this month."""
        return max(0, self.monthly_uploads_limit - self.uploads_used_this_month)
    
    def get_renders_remaining(self) -> int:
        """Get remaining renders for this month."""
        return max(0, self.monthly_renders_limit - self.renders_used_this_month)
    
    def reset_monthly_usage(self):
        """Reset monthly usage counters."""
        self.uploads_used_this_month = 0
        self.renders_used_this_month = 0
