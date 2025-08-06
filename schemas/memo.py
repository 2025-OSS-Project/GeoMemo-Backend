from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class LocationSchema(BaseModel):
    name: str
    latitude: float
    longitude: float
    address: str
    category: str

class UserSchema(BaseModel):
    userId: int
    username: str
    photoUrl: Optional[str]

class MemoSchema(BaseModel):
    memoId: int
    content: str
    createdAt: datetime
    updatedAt: datetime
    isPublic: bool
    fileUrl: List[str]
    location: LocationSchema
    user: UserSchema

class CreateMemoRequest(BaseModel):
    content: str
    is_public: bool
    user_id: int
    location_name: str
    location_latitude: float
    location_longitude: float
    location_address: str
    location_category: str
    file_url: str


class UpdateMemoRequest(BaseModel):
    memo_id: int
    content: str
    is_public: bool
    remain_photo_ids: list[int]
    new_photo_urls: list[str]

