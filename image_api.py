from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database_connection import get_db
from minio_service import minio_service
from auth_dependencies import get_current_user
from database import User
from typing import List
from pydantic import BaseModel
from io import BytesIO
from database import ImageMetadata


router = APIRouter(prefix="/images", tags=["Images"])

class ImageResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    object_name: str
    size: int
    content_type: str
    url: str
    user_id: int

class ImageListResponse(BaseModel):
    images: List[ImageResponse]
    total: int

@router.post("/upload", response_model=ImageResponse)
async def upload_image(
    file: UploadFile,
    folder: str = "images",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    upload_result = await minio_service.upload_image(
        file=file,
        folder=folder,
        user_id=current_user.id
    )

    
    image_metadata = ImageMetadata(
        filename=upload_result["filename"],
        original_filename=upload_result["original_filename"],
        object_name=upload_result["object_name"],
        size=upload_result["size"],
        content_type=upload_result["content_type"],
        bucket=upload_result["bucket"],
        user_id=current_user.id
    )

    db.add(image_metadata)
    await db.commit()
    await db.refresh(image_metadata)

    # generate image
    url = minio_service.get_image_url(upload_result["object_name"])

    return {
        **upload_result,
        "id": image_metadata.id,
        "url": url,
        "user_id": current_user.id
    }



@router.get("/{image_id}", response_class=StreamingResponse)
async def get_image(
    image_id: int,
    db: AsyncSession = Depends(get_db)
):
    from database import ImageMetadata
    from sqlalchemy import select
    
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
            "Content-Disposition": f"inline; filename={image.filename}"
        }
    )


@router.get("/", response_model=ImageListResponse)
async def list_my_images(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    
    from database import ImageMetadata
    from sqlalchemy import select
    
    result = await db.execute(
        select(ImageMetadata).where(ImageMetadata.user_id == current_user.id)
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
            "url": url,
            "user_id": img.user_id
        })
    
    return {
        "images": image_list,
        "total": len(image_list)
    }
