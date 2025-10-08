from rest_framework import serializers
from .models import Meal
import json

class MealSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()  # CHANGE: Make this a method field
    
    class Meta:
        model = Meal
        fields = ['id', 'image', 'foods_data', 'meal_time', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_image(self, obj):  # ADD: This method to get MinIO URL
        """Get full MinIO URL for image"""
        if obj.image:
            return obj.image.url  # This returns the MinIO URL
        return None
    
    def validate_foods_data(self, value):
        # ADD: Handle string JSON input
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("foods_data must be valid JSON")
        
        if not isinstance(value, dict) or 'foods' not in value:
            raise serializers.ValidationError("foods_data must contain a 'foods' array")
        if not isinstance(value['foods'], list):
            raise serializers.ValidationError("'foods' must be an array")
        return value

class MealCreateSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False)
    foods_data = serializers.JSONField()  # ADD: Specify as JSONField
    
    class Meta:
        model = Meal
        fields = ['image', 'foods_data', 'meal_time']
    
    def validate_foods_data(self, value):
        # ADD: Handle string JSON input
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("foods_data must be valid JSON")
        
        if not isinstance(value, dict) or 'foods' not in value:
            raise serializers.ValidationError("foods_data must contain a 'foods' array")
        if not isinstance(value['foods'], list):
            raise serializers.ValidationError("'foods' must be an array")
        return value

class MealListSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()  # CHANGE: Make this a method field
    
    class Meta:
        model = Meal
        fields = ['id', 'image', 'meal_time', 'created_at']
    
    def get_image(self, obj):  # ADD: This method to get MinIO URL
        """Get full MinIO URL for image"""
        if obj.image:
            return obj.image.url  # This returns the MinIO URL
        return None