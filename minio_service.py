from minio import Minio
from minio.error import S3Error
from fastapi import UploadFile, HTTPException
from io import BytesIO
from datetime import timedelta
import uuid
from typing import Optional
import config

class MinIOService:
    def __init__(self):
        self.client = Minio(
            config.MINIO_ENDPOINT,
            access_key=config.MINIO_ACCESS_KEY,
            secret_key=config.MINIO_SECRET_KEY,
            secure=config.MINIO_SECURE
        )
        self.bucket_name=config.MINIO_BUCKET_NAME
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        #Create bucket if it doesnt exists
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"Bucket '{self.bucket_name}' created")
            else:
                print(f"Bucket name already exists!")
        except S3Error as e:
            print(f"Error creating  bucket: {e}")
            raise
    
    async def upload_image(
        self, 
        file: UploadFile, 
        folder: str = "images",
        user_id: Optional[int] = None
    ) -> dict:
        try:
            #validation
            if not file.content_type.startswith("/image"):
                raise HTTPException(
                    status_code=400,
                    detail="Only image files are allowed"
                )
            
            file_extension = file.filename.split('.')[-1]
            unique_filename = f"{uuid.uuid4()}.{file_extension}"

            if user_id:
                object_name = f"{folder}/user_{user_id}/{unique_filename}"
            else:
                object_name = f"{folder}/{unique_filename}"

            file_content = await file.read()
            file_size = len(file_content)

            #upload to minIO
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=BytesIO(file_content),
                length=file_size,
                content_type=file.content_type
            )

            print(f"Upload file: {object_name}")

            return {
                "filename": unique_filename,
                "original_filename": file.filename,
                "object_name": object_name,
                "size": file_size,
                "content_type": file.content_type,
                "bucket": self.bucket_name
            }
        except S3Error as e:
            print(f"❌ MinIO Error: {e}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
        except Exception as e:
            print(f"❌ Error: {e}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")



    def get_image_url(self, object_name: str, expires: int = 3600) -> str:
            try:
                url = self.client.presigned_get_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    expires=timedelta(seconds=expires)
                )
                return url
            except S3Error as e:
                print(f"Error generating url: {e}")
                raise HTTPException(status_code=500, detail="Failed to generate image URL")
            
    def download_image(self, object_name: str) -> bytes:
            try:
                response = self.client.get_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name
                )
                data=response.read()
                response.close()
                response.release_conn()
                return data
            except S3Error as e:
                print(f"Error download: {e}")
                raise HTTPException(status_code=404, detail="Image not found")
        
    def delete_image(self, object_name: str) -> bool:
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name, 
                object_name=object_name
            )
            print(f"Delete object: {object_name}")
            return True
        except S3Error as e:
            print(f"Error deleting: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete image")
    
    def list_image(self, prefix: str = "") -> list:
        try:
            objects = self.client.list_objects(
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=True
            )
            return [obj.object_name for obj in objects]
        except S3Error as e:
            print(f"Error listing: {e}")
            return []


minio_service = MinIOService()
            