from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class LocationInfo(BaseModel):
    name: str
    latitude: float
    longitude: float
    address: str
    category: str

class UserInfo(BaseModel):
    userId: int 
    username: str
    photoUrl: str

class MemoResponse(BaseModel):
    memoId: int 
    content: str
    createdAt: datetime 
    updatedAt: datetime 
    isPublic: bool 
    fileUrl: str
