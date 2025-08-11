from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional, Dict

class PrivacyUpdateRequest(BaseModel):
    privacy_settings: Literal["open", "semi", "closed"]

class StandardResponse(BaseModel):
    success: bool
    error: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    nickname: str
    phone: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

#비밀번호 변경 스키마
class PasswordUpdateRequest(BaseModel):
    password: str
    new_password: str

class PasswordUpdateResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, str]]
    error: Optional[str]

class UserProfileImageUpdate(BaseModel):
    profile_image_url: str

#닉네임 변경 스키마
class NicknameUpdateRequest(BaseModel):
    nickname: str

class NicknameUpdateResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, str]]
    error: Optional[str]

#회원탈퇴 스키마
class DeleteUserResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, int]]
    error: Optional[str]

class ViewUpdateRequest(BaseModel):
    view_settings: Literal["all", "follows", "self"]

class UserProfileResponse(BaseModel):
    user_id: int
    user_profile: Optional[str] = None
    user_privacy: str
    user_nickname: str
    follower_count: int
    following_count: int    