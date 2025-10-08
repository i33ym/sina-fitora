from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from database_connection import get_db
from sms_schemas import SMSRequest, SMSResponse, VerifySMSRequest, SMSAuthResponse
from sms_service import create_sms_code, verify_sms_code
from user_service import get_or_create_user_by_phone, user_to_dict
from jwt_utils import create_access_token, create_refresh_token

router = APIRouter(prefix="/sms", tags=["SMS"])

@router.post("/send", response_model=SMSResponse)
async def send_sms(
    request: SMSRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        session_id, expires_in = await create_sms_code(db, request.phone)
        
        return SMSResponse(
            session=session_id,
            expires_in=expires_in,
            message=f"SMS code sent to {request.phone}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send SMS: {str(e)}"
        )

@router.post("/verify", response_model=SMSAuthResponse)
async def verify_sms(
    request: VerifySMSRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        is_valid, session_id = await verify_sms_code(db, request.session, request.code, request.phone)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired SMS code"
            )
        user = await get_or_create_user_by_phone(db, request.phone)
        token_data = {"sub": str(user.id), "email": user.email or request.phone}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return SMSAuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_to_dict(user),
            message=f"SMS verified and user authenticated for {request.phone}"
        )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify SMS and authenticate user: {str(e)}"
        )
