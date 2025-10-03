from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from database import UserModel
from profile_schemas import ProfileUpdateRequest
import logging

logger = logging.getLogger(__name__)

async def update_user_profile(
    db: AsyncSession, 
    user_id: int, 
    profile_data: ProfileUpdateRequest
) -> UserModel:
    try:
        result = await db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("User not found")
        
        update_data = {}
        for field, value in profile_data.dict().items():
            if value is not None:
                update_data[field] = value
        
        if not update_data:
            return user

        await db.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(**update_data)
        )
        
        await db.commit()
        await db.refresh(user)
        logger.info(f"Profile updated for user {user_id}: {list(update_data.keys())}")
        return user
        
    except Exception as e:
        logger.error(f"Error updating profile for user {user_id}: {str(e)}")
        await db.rollback()
        raise e

async def get_user_profile(db: AsyncSession, user_id: int) -> Optional[UserModel]:
    try:
        result = await db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        return result.scalar_one_or_none()
        
    except Exception as e:
        logger.error(f"Error getting profile for user {user_id}: {str(e)}")
        return None
