from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database_connection import get_db
from minio_service import minio_service
from auth_dependencies import get_current_user
from database import User, ImageMetadata
from typing import List
from pydantic import BaseModel
from io import BytesIO


router = APIRouter(prefix="/images", tags=["Images"])

class ImageResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    object_name: str
    size: int
    content_type: str
    url: str

class ImageListResponse(BaseModel):
    images: List[ImageResponse]
    total: int

@router.post("/upload", response_model=dict)
async def upload_image(
    file: UploadFile = File(...),
    folder: str = "images",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload an image and save metadata to database
    Returns: UUID of the uploaded image
    """
    # Upload to MinIO - now returns only UUID
    image_uuid = await minio_service.upload_image(
        file=file,
        folder=folder,
        user_id=current_user.id
    )
    
    file_extension = f".{file.filename.split('.')[-1].lower()}"
    unique_filename = f"{image_uuid}{file_extension}"
    object_name = f"{folder}/user_{current_user.id}/{unique_filename}"
    
    await file.seek(0)  # Reset file pointer
    file_content = await file.read()
    file_size = len(file_content)
    
    # Save metadata to database
    image_metadata = ImageMetadata(
        filename=unique_filename,
        original_filename=file.filename,
        object_name=object_name,
        size=file_size,
        content_type=file.content_type
    )
    
    db.add(image_metadata)
    await db.commit()
    await db.refresh(image_metadata)
    
    print(f"✓ Saved to database: ID={image_metadata.id}, UUID={image_uuid}")
    
    return {
        "uuid": image_uuid,
        "id": image_metadata.id,
        "message": "Image uploaded successfully"
    }


@router.get("/{image_id}", response_class=StreamingResponse)
async def get_image(
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get image by ID and stream it
    """
    # Get metadata from database
    result = await db.execute(
        select(ImageMetadata).where(ImageMetadata.id == image_id)
    )
    image = result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Download from MinIO
    image_data = minio_service.download_image(image.object_name)
    
    # Return as streaming response
    return StreamingResponse(
        BytesIO(image_data),
        media_type=image.content_type,
        headers={
            "Content-Disposition": f"inline; filename={image.original_filename}"
        }
    )


@router.get("/", response_model=ImageListResponse)
async def list_my_images(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all images for the current user
    """
    result = await db.execute(
        select(ImageMetadata).where(ImageMetadata.id == current_user.id)
    )
    images = result.scalars().all()
    
    # Generate URLs for all images
    image_list = []
    for img in images:
        url = minio_service.get_image_url(img.object_name)
        image_list.append({
            "id": img.id,
            "filename": img.filename,
            "original_filename": img.original_filename,
            "object_name": img.object_name,
            "size": img.size,
            "content_type": img.content_type,
            "url": url
        })
    
    return {
        "images": image_list,
        "total": len(image_list)
    }


@router.delete("/{image_id}")
async def delete_image(
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an image
    """
    # Get image from database
    result = await db.execute(
        select(ImageMetadata).where(ImageMetadata.id == image_id)
    )
    image = result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Delete from MinIO
    minio_service.delete_image(image.object_name)
    
    # Delete from database
    await db.delete(image)
    await db.commit()
    
    return {"message": "Image deleted successfully"}