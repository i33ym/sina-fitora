from rest_framework import serializers
from .models import ImageMetadata
from drf_spectacular.utils import extend_schema_field, OpenApiTypes

class ImageMetadataSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    
    class Meta:
        model = ImageMetadata
        fields = ['id', 'filename', 'original_filename', 'object_name', 
                  'size', 'content_type', 'created_at', 'url']
        read_only_fields = ['id', 'created_at']
    
    @extend_schema_field(OpenApiTypes.STR)
    def get_url(self, obj):
        from .minio_service import minio_service
        return minio_service.get_image_url(obj.object_name)


class ImageUploadSerializer(serializers.Serializer):
    file = serializers.ImageField(required=True, help_text="Image file to upload")
    folder = serializers.CharField(
        default='images', 
        required=False,
        help_text="Folder name in MinIO bucket"
    )