from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from database_connection import get_db
from database import UserModel
from auth_schemas import GoogleAuthRequest, TokenResponse, RefreshTokenRequest
from user_service import get_or_create_user_from_google, user_to_dict
from jwt_utils import create_access_token, create_refresh_token, verify_token
from auth_dependencies import get_current_user
from typing import Dict, Any

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/google", response_model=TokenResponse)
async def google_auth(
    auth_request: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        user = await get_or_create_user_from_google(
            db, 
            auth_request.google_token, 
            auth_request.fcm_token
        )
        
        token_data = {"sub": str(user.id), "email": user.email}
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_to_dict(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )

@router.post("/refresh", response_model=Dict[str, str])
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        payload = verify_token(refresh_request.refresh_token, "refresh")
        user_id = int(payload.get("sub"))
        token_data = {"sub": str(user_id), "email": payload.get("email")}
        access_token = create_access_token(token_data)
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.get("/me")
async def get_current_user_profile(
    current_user: UserModel = Depends(get_current_user)
):
    return {"user": user_to_dict(current_user)}
