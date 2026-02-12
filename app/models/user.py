"""User model."""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, Integer, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class UserRole(str, PyEnum):
    """User roles."""
    USER = "user"
    PRO = "pro"
    AGENCY = "agency"
    ADMIN = "admin"


class User(Base):
    """User model for authentication and profile."""
    
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Role & Status
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.USER,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Usage tracking
    uploads_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clips_generated_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    render_credits: Mapped[int] = mapped_column(Integer, default=10, nullable=False)  # Free tier
    
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
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    videos: Mapped[List["Video"]] = relationship("Video", back_populates="user", lazy="selectin")
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="user", lazy="selectin")
    subscription: Mapped[Optional["Subscription"]] = relationship("Subscription", back_populates="user", uselist=False, lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"
    
    def has_active_subscription(self) -> bool:
        """Check if user has an active subscription."""
        if not self.subscription:
            return False
        return self.subscription.is_active()
    
    def can_upload(self) -> bool:
        """Check if user can upload more videos."""
        if self.role in [UserRole.PRO, UserRole.AGENCY, UserRole.ADMIN]:
            return True
        return self.uploads_count < 5  # Free tier: 5 uploads
    
    def can_render(self) -> bool:
        """Check if user can render clips."""
        if self.role in [UserRole.PRO, UserRole.AGENCY, UserRole.ADMIN]:
            return True
        return self.render_credits > 0
