"""User service."""
from datetime import datetime
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.models.subscription import Subscription, SubscriptionPlan
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """User service for user management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()
    
    async def create(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Create user
        user = User(
            email=user_data.email.lower(),
            hashed_password=hash_password(user_data.password),
            full_name=user_data.full_name,
            role=UserRole.USER
        )
        
        self.db.add(user)
        await self.db.flush()
        
        # Create free subscription
        subscription = Subscription(
            user_id=user.id,
            plan=SubscriptionPlan.FREE,
            monthly_uploads_limit=5,
            monthly_renders_limit=10,
            storage_gb_limit=1
        )
        self.db.add(subscription)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await self.get_by_email(email)
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        return user
    
    async def update(self, user_id: str, user_data: UserUpdate) -> User:
        """Update user information."""
        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        update_data = user_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def update_last_login(self, user_id: str) -> None:
        """Update user's last login time."""
        user = await self.get_by_id(user_id)
        if user:
            user.last_login_at = datetime.utcnow()
            await self.db.commit()
    
    async def update_avatar(self, user_id: str, avatar_url: str) -> User:
        """Update user avatar."""
        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        user.avatar_url = avatar_url
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def delete(self, user_id: str) -> None:
        """Delete user."""
        user = await self.get_by_id(user_id)
        if user:
            await self.db.delete(user)
            await self.db.commit()
    
    async def get_stats(self, user_id: str) -> dict:
        """Get user statistics."""
        from app.models.video import Video
        from app.models.clip import Clip
        
        # Count videos
        videos_result = await self.db.execute(
            select(func.count(Video.id)).where(Video.user_id == user_id)
        )
        videos_count = videos_result.scalar() or 0
        
        # Count clips
        clips_result = await self.db.execute(
            select(func.count(Clip.id)).where(Clip.user_id == user_id)
        )
        clips_count = clips_result.scalar() or 0
        
        # Count completed clips
        completed_clips_result = await self.db.execute(
            select(func.count(Clip.id)).where(
                Clip.user_id == user_id,
                Clip.status == "completed"
            )
        )
        completed_clips_count = completed_clips_result.scalar() or 0
        
        return {
            "videos_count": videos_count,
            "clips_count": clips_count,
            "completed_clips_count": completed_clips_count,
        }
    
    async def increment_uploads(self, user_id: str) -> None:
        """Increment user's upload count."""
        user = await self.get_by_id(user_id)
        if user:
            user.uploads_count += 1
            await self.db.commit()
    
    async def increment_clips_generated(self, user_id: str) -> None:
        """Increment user's clips generated count."""
        user = await self.get_by_id(user_id)
        if user:
            user.clips_generated_count += 1
            await self.db.commit()
    
    async def deduct_render_credit(self, user_id: str) -> bool:
        """Deduct a render credit from user."""
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        if user.role in [UserRole.PRO, UserRole.AGENCY, UserRole.ADMIN]:
            return True
        
        if user.render_credits > 0:
            user.render_credits -= 1
            await self.db.commit()
            return True
        
        return False
