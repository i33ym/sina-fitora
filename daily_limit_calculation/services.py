# daily_limit_calculation/services.py

import json
import logging
import re
from typing import Dict, List, Any
from datetime import date

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)


class DailyLimitsCalculator:
    """
    Calculates personalized daily ingredient limits based on user profile.
    Uses OpenAI API to generate nutritionally sound recommendations.
    
    SOLID Principles:
    - Single Responsibility: Only calculates limits
    - Dependency Inversion: Injected OpenAI client
    """
    
    # RDI defaults (Recommended Dietary Intake)
    RDI_DEFAULTS = {
        'calories': 2000,
        'protein': 50,
        'fat': 65,
        'carbs': 300,
        'fiber': 25,
        'cholesterol': 300,
        'saturated_fat': 20,
        'unsaturated_fat': 45,
        'omega_3': 1.6,
        'omega_6': 12,
        'calcium': 1000,
        'iron': 18,
        'magnesium': 400,
        'potassium': 3500,
        'zinc': 11,
        'sodium': 2300,
        'vitamin_a': 900,
        'vitamin_b6': 1.7,
        'vitamin_b9': 400,
        'vitamin_b12': 2.4,
        'vitamin_c': 90,
        'vitamin_d': 20,
        'vitamin_e': 15,
        'vitamin_k': 120,
        'selenium': 55,
    }
    
    def __init__(self):
        """Initialize with OpenAI client"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-4')
    
    def calculate_from_user(self, user) -> Dict[str, float]:
        """
        Main entry point: Takes User object and generates personalized limits.
        Extracts survey data directly from User model fields.
        
        Args:
            user: User instance with fields:
                - date_of_birth: DateField
                - gender: str (male/female)
                - current_weight: float (kg)
                - current_height: float (cm)
                - activeness_level: str
                - goal: str
                - diet_restrictions: ArrayField (list)
                - preferred_diet: str
        
        Returns:
            List of dicts: [{"name": "calories", "daily_norm": 2000}, ...]
        
        Raises:
            ValueError: If user data is invalid
            Exception: If OpenAI API fails
        """
        
        # Extract survey data from user fields
        survey_data = self._extract_user_data(user)
        
        # Validate input
        if not self._validate_survey_data(survey_data):
            raise ValueError("Invalid user data provided")
        
        # Build prompt for AI
        prompt = self._build_calculation_prompt(survey_data)
        
        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a nutrition expert. Generate personalized daily dietary limits in JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Low temp for consistent results
                max_tokens=2000,
            )
            
            # Extract and parse response
            ai_response = response.choices[0].message.content
            ingredients_summary = self._parse_ai_response(ai_response)
            
            logger.info(f"Successfully calculated limits for user with age {survey_data.get('age')}")
            return ingredients_summary
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    def _extract_user_data(self, user) -> Dict[str, Any]:
        """
        Extract survey data from User model fields.
        Converts User model fields to survey_data dictionary format.
        """
        
        # Calculate age from date_of_birth
        age = None
        if user.date_of_birth:
            today = date.today()
            age = today.year - user.date_of_birth.year - (
                (today.month, today.day) < (user.date_of_birth.month, user.date_of_birth.day)
            )
        
        # Map activeness_level choices to normalized form
        activity_level_mapping = {
            'sedentary': 'sedentary',
            'lightly_active': 'light',
            'moderately_active': 'moderate',
            'very_active': 'active',
            'extremely_active': 'very_active',
        }
        
        # Map goal choices
        goal_mapping = {
            'lose_weight': 'lose_weight',
            'gain_weight': 'gain_muscle',
            'maintain_weight': 'maintain',
        }
        
        survey_data = {
            'age': age,
            'gender': user.gender,  # male/female
            'weight': user.current_weight,  # kg
            'height': user.current_height,  # cm
            'activity_level': activity_level_mapping.get(user.activeness_level, 'moderate'),
            'goal': goal_mapping.get(user.goal, 'maintain'),
            'dietary_restrictions': user.diet_restrictions or [],  # ArrayField
            'preferred_diet': user.preferred_diet,  # keto/low_carbs/etc
        }
        
        return survey_data
    
    def _validate_survey_data(self, survey_data: Dict[str, Any]) -> bool:
        """Validate required fields exist in survey data"""
        required_fields = ['age', 'gender', 'weight', 'height', 'activity_level', 'goal']
        
        # Check all required fields exist
        if not all(field in survey_data for field in required_fields):
            return False
        
        # Check values are not None
        if any(survey_data.get(field) is None for field in required_fields):
            return False
        
        # Check numeric values are positive
        if survey_data.get('weight', 0) <= 0 or survey_data.get('height', 0) <= 0:
            return False
        
        return True
    
    def _build_calculation_prompt(self, survey_data: Dict[str, Any]) -> str:
        """Build the prompt to send to OpenAI for calculation"""
        
        restrictions = survey_data.get('dietary_restrictions', [])
        restriction_text = ", ".join(restrictions) if restrictions else "None"
        
        prompt = f"""
Based on the following user profile, calculate personalized daily dietary limits:

USER PROFILE:
- Age: {survey_data['age']} years
- Gender: {survey_data['gender']}
- Weight: {survey_data['weight']} kg
- Height: {survey_data['height']} cm
- Activity Level: {survey_data['activity_level']}
- Goal: {survey_data['goal']}
- Dietary Restrictions: {restriction_text}
- Preferred Diet Type: {survey_data.get('preferred_diet', 'balanced')}

INSTRUCTIONS:
1. Calculate BMR (Basal Metabolic Rate) using Mifflin-St Jeor equation
2. Apply activity level multiplier to get TDEE (Total Daily Energy Expenditure)
3. Adjust calories based on goal:
   - lose_weight: -500 calories (0.5kg/week deficit)
   - gain_muscle: +300 calories surplus
   - maintain: no adjustment
4. Calculate macro targets based on goal and diet type
5. Apply dietary restrictions
6. Return EXACT JSON format below - NO other text

REQUIRED JSON FORMAT (return ONLY valid JSON):
{{
  "ingredients_summary": [
    {{"name": "calories", "daily_norm": NUMBER}},
    {{"name": "protein", "daily_norm": NUMBER}},
    {{"name": "fat", "daily_norm": NUMBER}},
    {{"name": "carbs", "daily_norm": NUMBER}},
    {{"name": "fiber", "daily_norm": NUMBER}},
    {{"name": "cholesterol", "daily_norm": NUMBER}},
    {{"name": "saturated_fat", "daily_norm": NUMBER}},
    {{"name": "unsaturated_fat", "daily_norm": NUMBER}},
    {{"name": "omega_3", "daily_norm": NUMBER}},
    {{"name": "omega_6", "daily_norm": NUMBER}},
    {{"name": "calcium", "daily_norm": NUMBER}},
    {{"name": "iron", "daily_norm": NUMBER}},
    {{"name": "magnesium", "daily_norm": NUMBER}},
    {{"name": "potassium", "daily_norm": NUMBER}},
    {{"name": "zinc", "daily_norm": NUMBER}},
    {{"name": "sodium", "daily_norm": NUMBER}},
    {{"name": "vitamin_a", "daily_norm": NUMBER}},
    {{"name": "vitamin_b6", "daily_norm": NUMBER}},
    {{"name": "vitamin_b9", "daily_norm": NUMBER}},
    {{"name": "vitamin_b12", "daily_norm": NUMBER}},
    {{"name": "vitamin_c", "daily_norm": NUMBER}},
    {{"name": "vitamin_d", "daily_norm": NUMBER}},
    {{"name": "vitamin_e", "daily_norm": NUMBER}},
    {{"name": "vitamin_k", "daily_norm": NUMBER}},
    {{"name": "selenium", "daily_norm": NUMBER}}
  ]
}}

Return ONLY the JSON object, no additional text.
"""
        return prompt
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, float]:
        """Parse AI response and convert to key-value format"""
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError(f"Could not parse JSON from response: {response_text}")
    
        # Extract ingredients_summary
        if 'ingredients_summary' not in data:
            raise ValueError("Response missing 'ingredients_summary' key")
        
        ingredients = data['ingredients_summary']
        
        # Validate each ingredient
        if not isinstance(ingredients, list):
            raise ValueError("ingredients_summary must be a list")
    
    # Convert to key-value format
        ingredients_dict = {}
        for ingredient in ingredients:
            if not isinstance(ingredient, dict):
                raise ValueError("Each ingredient must be a dictionary")
            if 'name' not in ingredient or 'daily_norm' not in ingredient:
                raise ValueError("Each ingredient must have 'name' and 'daily_norm' keys")
            
            # Convert daily_norm to float
            try:
                ingredients_dict[ingredient['name']] = float(ingredient['daily_norm'])
            except (ValueError, TypeError):
                raise ValueError(f"Invalid daily_norm for {ingredient.get('name')}")
    
        logger.debug(f"Successfully parsed {len(ingredients_dict)} ingredients from AI response")
        return ingredients_dict
    
    def get_fallback_limits(self, survey_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fallback limits if AI API fails.
        Based on standard RDI with basic adjustments.
        """
        logger.warning("Using fallback limits - AI calculation failed")
        
        # Simple fallback: use RDI defaults
        return [
            {"name": key, "daily_norm": value}
            for key, value in self.RDI_DEFAULTS.items()
        ]