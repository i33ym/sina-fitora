# daily_limit_calculation/serializers.py

from rest_framework import serializers
from .models import DailyIngredientsLimit


class IngredientSummarySerializer(serializers.Serializer):
    """Serializer for individual ingredient in the summary"""
    
    name = serializers.CharField(max_length=50)
    daily_norm = serializers.FloatField(min_value=0)
    
    def validate_name(self, value):
        """Validate ingredient name is lowercase"""
        if not value.islower():
            raise serializers.ValidationError(
                "Ingredient name should be lowercase"
            )
        return value


class DailyIngredientsLimitSerializer(serializers.ModelSerializer):
    """Main serializer for DailyIngredientsLimit model"""
    
    user_email = serializers.CharField(
        source='user.email',
        read_only=True
    )
    
    ingredients_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DailyIngredientsLimit
        fields = [
            'id',
            'user_email',
            'ingredients_summary',
            'ingredients_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'user_email',
            'created_at',
            'updated_at',
        ]
    
    def get_ingredients_count(self, obj):
        """Return count of ingredients"""
        return len(obj.ingredients_summary) if obj.ingredients_summary else 0
    
    def validate_ingredients_summary(self, value):
        """Validate ingredients_summary structure"""
        if not isinstance(value, list):
            raise serializers.ValidationError(
                "ingredients_summary must be a list"
            )
        
        if len(value) < 10:
            raise serializers.ValidationError(
                "ingredients_summary must contain at least 10 ingredients"
            )
        
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError(
                    "Each ingredient must be a dictionary"
                )
            if 'name' not in item or 'daily_norm' not in item:
                raise serializers.ValidationError(
                    "Each ingredient must have 'name' and 'daily_norm' fields"
                )
            
            # Validate name is string
            if not isinstance(item['name'], str):
                raise serializers.ValidationError(
                    f"Ingredient name must be string, got {type(item['name'])}"
                )
            
            # Validate daily_norm is numeric
            try:
                float(item['daily_norm'])
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    f"daily_norm for {item['name']} must be numeric"
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
        
        ingredients_with_progress = []
        for ingredient in obj.ingredients_summary:
            name = ingredient['name']
            daily_norm = ingredient['daily_norm']
            consumed = today_consumption.get(name, 0)
            remaining = daily_norm - consumed
            percentage = (consumed / daily_norm * 100) if daily_norm > 0 else 0
            
            ingredients_with_progress.append({
                'name': name,
                'daily_norm': daily_norm,
                'consumed_today': consumed,
                'remaining': remaining,
                'percentage': round(percentage, 2),
                'status': self._get_status(percentage),
            })
        
        return ingredients_with_progress
    
    @staticmethod
    def _get_status(percentage):
        """Determine status based on percentage consumed"""
        if percentage < 0:
            return 'under'  # Haven't started
        elif percentage < 50:
            return 'low'  # Just started
        elif percentage < 85:
            return 'on_track'  # Good progress
        elif percentage < 100:
            return 'almost_reached'  # Nearly at limit
        elif percentage == 100:
            return 'at_limit'  # Exactly at limit
        else:
            return 'over'  # Over the limit


class QuickAccessLimitsSerializer(serializers.Serializer):
    """Simplified serializer with quick-access macros"""
    
    calories = serializers.SerializerMethodField()
    protein = serializers.SerializerMethodField()
    fat = serializers.SerializerMethodField()
    carbs = serializers.SerializerMethodField()
    fiber = serializers.SerializerMethodField()
    sodium = serializers.SerializerMethodField()
    vitamin_d = serializers.SerializerMethodField()
    
    def get_calories(self, obj):
        ingredient = obj.get_ingredient('calories')
        return ingredient['daily_norm'] if ingredient else None
    
    def get_protein(self, obj):
        ingredient = obj.get_ingredient('protein')
        return ingredient['daily_norm'] if ingredient else None
    
    def get_fat(self, obj):
        ingredient = obj.get_ingredient('fat')
        return ingredient['daily_norm'] if ingredient else None
    
    def get_carbs(self, obj):
        ingredient = obj.get_ingredient('carbs')
        return ingredient['daily_norm'] if ingredient else None
    
    def get_fiber(self, obj):
        ingredient = obj.get_ingredient('fiber')
        return ingredient['daily_norm'] if ingredient else None
    
    def get_sodium(self, obj):
        ingredient = obj.get_ingredient('sodium')
        return ingredient['daily_norm'] if ingredient else None
    
    def get_vitamin_d(self, obj):
        ingredient = obj.get_ingredient('vitamin_d')
        return ingredient['daily_norm'] if ingredient else None