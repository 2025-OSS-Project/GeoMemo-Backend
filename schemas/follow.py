from pydantic import BaseModel
from typing import Optional, Literal

class FollowActionResponse(BaseModel):
    success: bool
    error: Optional[str] = None

class FollowUserSummary(BaseModel):
    email: str
    nickname: str
    profileImageUrl: Optional[str]
    status: Literal["pending", "approved"]

class FollowListResponse(BaseModel):
    success: bool
    data: Optional[dict]
    error: Optional[str]