# daily_limit_calculation/serializers.py

from rest_framework import serializers
from .models import DailyIngredientsLimit


class DailyIngredientsLimitSerializer(serializers.ModelSerializer):
    """Main serializer for DailyIngredientsLimit model"""
    
    user_email = serializers.CharField(
        source='user.email',
        read_only=True
    )
    
    class Meta:
        model = DailyIngredientsLimit
        fields = [
            'id',
            'user_email',
            'ingredients_summary',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'user_email',
            'created_at',
            'updated_at',
        ]
    
    def validate_ingredients_summary(self, value):
        """Validate ingredients_summary structure (dict format)"""
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "ingredients_summary must be a dictionary"
            )
        
        if len(value) < 10:
            raise serializers.ValidationError(
                "ingredients_summary must contain at least 10 ingredients"
            )
        
        for name, norm in value.items():
            if not isinstance(name, str):
                raise serializers.ValidationError(
                    "Ingredient name must be string"
                )
            
            try:
                float(norm)
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    f"daily_norm for {name} must be numeric"
                )
        
        return value


class DailyLimitsWithProgressSerializer(serializers.Serializer):
    """Extended serializer including user progress against limits"""
    
    id = serializers.UUIDField(read_only=True)
    user_email = serializers.CharField(read_only=True)
    
    ingredients = serializers.SerializerMethodField()
    
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    def get_ingredients(self, obj):
        """
        Transform ingredients_summary to include progress info.
        Requires 'today_consumption' in context.
        """
        today_consumption = self.context.get('today_consumption', {})
        
        ingredients_with_progress = {}
        for name, daily_norm in obj.ingredients_summary.items():
            consumed = today_consumption.get(name, 0)
            remaining = daily_norm - consumed
            percentage = (consumed / daily_norm * 100) if daily_norm > 0 else 0
            
            ingredients_with_progress[name] = {
                'daily_norm': daily_norm,
                'consumed_today': consumed,
                'remaining': remaining,
                'percentage': round(percentage, 2),
                'status': self._get_status(percentage),
            }
        
        return ingredients_with_progress
    
    @staticmethod
    def _get_status(percentage):
        """Determine status based on percentage consumed"""
        if percentage < 0:
            return 'under'
        elif percentage < 50:
            return 'low'
        elif percentage < 85:
            return 'on_track'
        elif percentage < 100:
            return 'almost_reached'
        elif percentage == 100:
            return 'at_limit'
        else:
            return 'over'


class QuickAccessLimitsSerializer(serializers.Serializer):
    """Simplified serializer with quick-access macros"""
    
    calories = serializers.SerializerMethodField()
    protein = serializers.SerializerMethodField()
    fat = serializers.SerializerMethodField()
    carbs = serializers.SerializerMethodField()
    
    def get_calories(self, obj):
        return obj.ingredients_summary.get('calories')
    
    def get_protein(self, obj):
        return obj.ingredients_summary.get('protein')
    
    def get_fat(self, obj):
        return obj.ingredients_summary.get('fat')
    
    def get_carbs(self, obj):
        return obj.ingredients_summary.get('carbs')