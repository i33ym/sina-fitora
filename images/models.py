from django.db import models
from django.conf import settings

class ImageMetadata(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='images')
    filename = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    object_name = models.CharField(max_length=500, unique=True)
    size = models.BigIntegerField()
    content_type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'image_metadata'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.original_filename} - {self.user.email}"