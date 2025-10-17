from django.db import models
import uuid


class DailyIngredientsLimit(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='daily_limits'
    )
    
    ingredients_summary = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'daily_ingredients_limits'
        verbose_name = 'Daily Ingredients Limit'
        verbose_name_plural = 'Daily Ingredients Limits'
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Daily Limits - {self.user.email}"
    
    INGREDIENTS = [
        'calories', 'protein', 'fat', 'carbs', 'fiber',
        'cholesterol', 'saturated_fat', 'unsaturated_fat',
        'omega_3', 'omega_6', 'calcium', 'iron', 'magnesium',
        'potassium', 'zinc', 'sodium', 'vitamin_a', 'vitamin_b6',
        'vitamin_b9', 'vitamin_b12', 'vitamin_c', 'vitamin_d',
        'vitamin_e', 'vitamin_k', 'selenium'
    ]
    
    def __getattr__(self, name):
        """Automatically handle *_target properties"""
        if name.endswith('_target'):
            ingredient_name = name[:-7]
            if ingredient_name in self.INGREDIENTS:
                ingredient = self.get_ingredient(ingredient_name)
                return ingredient['daily_norm'] if ingredient else None
        raise AttributeError(f"No attribute: {name}")
    
    def get_ingredient(self, ingredient_name):
        """Get specific ingredient by name"""
        for ingredient in self.ingredients_summary:
            if ingredient['name'] == ingredient_name:
                return ingredient
        return None
    
    @property
    def is_valid(self):
        """Check if ingredients_summary has required structure"""
        if not isinstance(self.ingredients_summary, list):
            return False
        if len(self.ingredients_summary) < 10:
            return False
        return all(
            isinstance(item, dict) and 
            'name' in item and 
            'daily_norm' in item
            for item in self.ingredients_summary
        )
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': str(self.id),
            'user_id': str(self.user.id),
            'ingredients_summary': self.ingredients_summary,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }