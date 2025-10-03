from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
from decimal import Decimal

class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    current_height: Optional[Decimal] = Field(None, description="Height in cm")
    current_weight: Optional[Decimal] = Field(None, description="Weight in kg")
    target_height: Optional[Decimal] = Field(None, description="Target height in cm")
    target_weight: Optional[Decimal] = Field(None, description="Target weight in kg")
    main_purpose: Optional[str] = None
    target_date: Optional[date] = None
    activeness_level: Optional[str] = None
    motivation: Optional[str] = None
    preferred_diet: Optional[str] = None
    diet_restrictions: Optional[List[str]] = None

class ProfileUpdateResponse(BaseModel):
    message: str = "Profile updated successfully"
    user: dict
