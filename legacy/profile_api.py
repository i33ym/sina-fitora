from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from database_connection import get_db
from database import UserModel
from auth_dependencies import get_current_user
from profile_schemas import ProfileUpdateRequest, ProfileUpdateResponse
from profile_service import update_user_profile
from user_service import user_to_dict

router = APIRouter(prefix="/profile", tags=["profile"])

@router.patch("/update", response_model=ProfileUpdateResponse)
async def update_profile(
    profile_data: ProfileUpdateRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        updated_user = await update_user_profile(db, current_user.id, profile_data)
        
        return ProfileUpdateResponse(
            user=user_to_dict(updated_user),
            message="Profile updated successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )
