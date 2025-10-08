from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from .models import ImageMetadata
from .serializers import ImageMetadataSerializer, ImageUploadSerializer
from .minio_service import minio_service


@extend_schema(
    request=ImageUploadSerializer,
    responses={
        201: {
            'type': 'object',
            'properties': {
                'uuid': {'type': 'string'},
                'id': {'type': 'integer'},
                'message': {'type': 'string'}
            }
        }
    },
    description="Upload an image to MinIO"
)
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsAuthenticated])
def upload_image(request):
    """Upload an image to MinIO"""
    serializer = ImageUploadSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    file = serializer.validated_data['file']
    folder = serializer.validated_data.get('folder', 'images')
    
    try:
        # Upload to MinIO
        image_uuid = minio_service.upload_image(
            file=file,
            folder=folder,
            user_id=request.user.id
        )
        
        # Create metadata
        file_extension = f".{file.name.split('.')[-1].lower()}"
        unique_filename = f"{image_uuid}{file_extension}"
        object_name = f"{folder}/user_{request.user.id}/{unique_filename}"
        
        image_metadata = ImageMetadata.objects.create(
            user=request.user,
            filename=unique_filename,
            original_filename=file.name,
            object_name=object_name,
            size=file.size,
            content_type=file.content_type
        )
        
        return Response({
            'uuid': image_uuid,
            'id': image_metadata.id,
            'message': 'Image uploaded successfully'
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    responses={200: ImageMetadataSerializer(many=True)},
    description="List all images for current user"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_images(request):
    """List all images for current user"""
    images = ImageMetadata.objects.filter(user=request.user)
    serializer = ImageMetadataSerializer(images, many=True)
    return Response({
        'images': serializer.data,
        'total': images.count()
    })


@extend_schema(
    responses={200: OpenApiTypes.BINARY},
    description="Get specific image by ID"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_image(request, image_id):
    """Get specific image"""
    try:
        image = ImageMetadata.objects.get(id=image_id, user=request.user)
        image_data = minio_service.download_image(image.object_name)
        
        response = HttpResponse(image_data, content_type=image.content_type)
        response['Content-Disposition'] = f'inline; filename={image.original_filename}'
        return response
        
    except ImageMetadata.DoesNotExist:
        return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    responses={200: {'type': 'object', 'properties': {'message': {'type': 'string'}}}},
    description="Delete an image"
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_image(request, image_id):
    """Delete an image"""
    try:
        image = ImageMetadata.objects.get(id=image_id, user=request.user)
        minio_service.delete_image(image.object_name)
        image.delete()
        
        return Response({'message': 'Image deleted successfully'})
    except ImageMetadata.DoesNotExist:
        return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)