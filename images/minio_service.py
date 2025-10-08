from minio import Minio
from minio.error import S3Error
from io import BytesIO
from datetime import timedelta
import uuid
from typing import Optional
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile

class MinIOService:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"✓ Bucket '{self.bucket_name}' created")
        except S3Error as e:
            print(f"✗ Error creating bucket: {e}")

    def upload_image(
        self, 
        file: InMemoryUploadedFile, 
        folder: str = "images",
        user_id: Optional[int] = None
    ) -> str:
        """Upload image and return UUID"""
        try:
            image_uuid = str(uuid.uuid4())
            file_extension = f".{file.name.split('.')[-1].lower()}"
            unique_filename = f"{image_uuid}{file_extension}"

            if user_id:
                object_name = f"{folder}/user_{user_id}/{unique_filename}"
            else:
                object_name = f"{folder}/{unique_filename}"
            
            file_content = file.read()
            file_size = len(file_content)

            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=BytesIO(file_content),
                length=file_size,
                content_type=file.content_type
            )
            print(f"✓ Uploaded: {object_name}")

            return image_uuid
        
        except S3Error as e:
            print(f"✗ MinIO Error: {e}")
            raise Exception(f"Upload failed: {str(e)}")
        except Exception as e:
            print(f"✗ Error: {e}")
            raise Exception(f"Upload failed: {str(e)}")
    
    def get_image_url(self, object_name: str, expires: int = 3600) -> str:
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=expires)
            )
            return url
        except S3Error as e:
            print(f"✗ Error generating URL: {e}")
            raise Exception("Failed to generate image URL")
    
    def download_image(self, object_name: str) -> bytes:
        try:
            response = self.client.get_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            print(f"✗ Error downloading: {e}")
            raise Exception("Image not found")
    
    def delete_image(self, object_name: str) -> bool:
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name, 
                object_name=object_name
            )
            print(f"✓ Deleted object: {object_name}")
            return True
        except S3Error as e:
            print(f"✗ Error deleting: {e}")
            raise Exception("Failed to delete image")

# Global instance
minio_service = MinIOService()