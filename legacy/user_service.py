from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from database import UserModel
from auth_service_simple import verify_google_token_simple as verify_google_token
from datetime import datetime

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[UserModel]:
    result = await db.execute(
        select(UserModel).where(UserModel.email == email)
    )
    return result.scalar_one_or_none()

async def get_user_by_phone(db: AsyncSession, phone: str) -> Optional[UserModel]:
    result = await db.execute(
        select(UserModel).where(UserModel.phone == phone)
    )
    return result.scalar_one_or_none()

async def get_user_by_google_id(db: AsyncSession, google_id: str) -> Optional[UserModel]:
    result = await db.execute(
        select(UserModel).where(UserModel.google_id == google_id)
    )
    return result.scalar_one_or_none()

async def create_user_from_google(db: AsyncSession, google_info: Dict[str, Any], fcm_token: Optional[str] = None) -> UserModel:
    user = UserModel(
        email=google_info['email'],
        google_id=google_info['google_id'],
        verified=google_info.get('email_verified', False),
        first_name=google_info.get('given_name'),
        last_name=google_info.get('family_name'),
        fcm_token=fcm_token,
        created_at=datetime.utcnow()
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def update_user_fcm_token(db: AsyncSession, user_id: int, fcm_token: str) -> Optional[UserModel]:
    await db.execute(
        update(UserModel)
        .where(UserModel.id == user_id)
        .values(fcm_token=fcm_token)
    )
    await db.commit()
    result = await db.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    return result.scalar_one_or_none()

async def get_or_create_user_from_google(db: AsyncSession, google_token: str, fcm_token: Optional[str] = None) -> UserModel:
    google_info = await verify_google_token(google_token)
    user = await get_user_by_google_id(db, google_info['google_id'])
    
    if user:
        if fcm_token and fcm_token != user.fcm_token:
            user = await update_user_fcm_token(db, user.id, fcm_token)
        return user
    user = await get_user_by_email(db, google_info['email'])
    
    if user:
        user.google_id = google_info['google_id']
        user.verified = google_info.get('email_verified', user.verified)
        if fcm_token:
            user.fcm_token = fcm_token
        
        await db.commit()
        await db.refresh(user)
        return user

    return await create_user_from_google(db, google_info, fcm_token)

async def create_user_from_phone(db: AsyncSession, phone: str) -> UserModel:
    user = UserModel(
        email=phone,
        phone=phone,
        verified=True,
        created_at=datetime.utcnow()
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def get_or_create_user_by_phone(db: AsyncSession, phone: str) -> UserModel:
    user = await get_user_by_phone(db, phone)
    
    if user:
        return user
    
    return await create_user_from_phone(db, phone)

def user_to_dict(user: UserModel) -> Dict[str, Any]:
    return {
        'id': user.id,
        'email': user.email,
        'phone': user.phone,
        'verified': user.verified,
        'google_id': user.google_id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'gender': user.gender,
        'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None,
        'current_height': float(user.current_height) if user.current_height else None,
        'current_weight': float(user.current_weight) if user.current_weight else None,
        'target_height': float(user.target_height) if user.target_height else None,
        'target_weight': float(user.target_weight) if user.target_weight else None,
        'main_purpose': user.main_purpose,
        'target_date': user.target_date.isoformat() if user.target_date else None,
        'activeness_level': user.activeness_level,
        'motivation': user.motivation,
        'preferred_diet': user.preferred_diet,
        'diet_restrictions': user.diet_restrictions,
        'version': user.version,
        'created_at': user.created_at.isoformat()
    }
