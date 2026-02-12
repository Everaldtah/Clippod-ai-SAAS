"""Subscription schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.subscription import SubscriptionPlan, SubscriptionStatus


class SubscriptionPlanInfo(BaseModel):
    """Subscription plan information."""
    plan: SubscriptionPlan
    name: str
    description: str
    price_monthly: float
    price_yearly: float
    features: list
    limits: dict


class SubscriptionResponse(BaseModel):
    """Subscription response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    
    # Plan info
    plan: SubscriptionPlan
    status: SubscriptionStatus
    
    # Billing
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool
    
    # Usage limits
    monthly_uploads_limit: int
    monthly_renders_limit: int
    storage_gb_limit: int
    
    # Current usage
    uploads_used_this_month: int
    renders_used_this_month: int
    storage_used_gb: float
    
    # Remaining
    uploads_remaining: int
    renders_remaining: int
    
    # Timestamps
    created_at: datetime
    updated_at: datetime


class SubscriptionCheckoutRequest(BaseModel):
    """Subscription checkout request schema."""
    plan: SubscriptionPlan
    billing_cycle: str = "monthly"  # monthly or yearly
    success_url: str
    cancel_url: str


class SubscriptionCheckoutResponse(BaseModel):
    """Subscription checkout response schema."""
    checkout_url: str
    session_id: str


class UsageResponse(BaseModel):
    """Usage response schema."""
    plan: SubscriptionPlan
    uploads_used: int
    uploads_limit: int
    uploads_remaining: int
    renders_used: int
    renders_limit: int
    renders_remaining: int
    storage_used_gb: float
    storage_limit_gb: int
