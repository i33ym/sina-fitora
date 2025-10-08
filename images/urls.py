from django.urls import path
from . import views

urlpatterns = [
    path('api/images/upload/', views.upload_image, name='upload_image'),
    path('api/images/', views.list_images, name='list_images'),
    path('api/images/<int:image_id>/', views.get_image, name='get_image'),
    path('api/images/<int:image_id>/delete/', views.delete_image, name='delete_image'),
]