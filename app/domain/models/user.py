from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from enum import Enum
from datetime import datetime

class RoleEnum(str, Enum):
    user = "user"
    tipster = "tipster"
    admin = "admin"

class SubscriptionEnum(str, Enum):
    free = "free"
    premium = "premium"

class ProfileBase(BaseModel):
    display_name: str = Field(..., max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = None

class ProfileCreate(ProfileBase):
    pass

class UserBase(BaseModel):
    uid: str = Field(..., description="Firebase UID", max_length=128)
    email: EmailStr
    role: RoleEnum = RoleEnum.user
    subscription: SubscriptionEnum = SubscriptionEnum.free

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int = Field(..., description="Internal DB ID")
    created_at: datetime
    profile: Optional[ProfileBase] = None

    class Config:
        from_attributes = True
