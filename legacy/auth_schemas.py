from pydantic import BaseModel, EmailStr
from typing import Optional

class GoogleAuthRequest(BaseModel):
    google_token: str
    fcm_token: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenData(BaseModel):
    access_token: str
    refresh_token: str
