from pydantic import BaseModel, validator
import re

class SMSRequest(BaseModel):
    phone: str
    
    @validator('phone')
    def validate_phone(cls, v):
        phone_digits = re.sub(r'\D', '', v)
        if len(phone_digits) < 10:
            raise ValueError('Phone number must have at least 10 digits')
        return v

class SMSResponse(BaseModel):
    session: str
    expires_in: int
    message: str = "SMS code sent successfully"

class VerifySMSRequest(BaseModel):
    session: str
    code: str
    phone: str

class SMSAuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict
    message: str = "SMS verified and user authenticated successfully"
