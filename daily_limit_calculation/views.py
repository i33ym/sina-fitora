import logging
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from .models import DailyIngredientsLimit
from .services import DailyLimitsCalculator
from .serializers import DailyIngredientsLimitSerializer, QuickAccessLimitsSerializer

logger = logging.getLogger(__name__)

@extend_schema(
    tags=['Daily Limit Calculation'],
    summary='Generate Daily Ingredient Limits',
    description='Generate personalized daily ingredient limits based on user profile',
)
class GenerateDailyLimitsView(APIView):
    """
    POST /api/daily-limits/generate/
    
    Generates personalized daily ingredient limits based on user profile.
    Creates or updates DailyIngredientsLimit record in database.
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Generate daily limits for authenticated user.
        Pulls data from user profile fields (date_of_birth, weight, height, goal, etc).
        """
        user = request.user
        
        # Validate user has completed profile
        if not user.profile_completed:
            return Response(
                {'error': 'User profile not completed yet'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate required fields
        required_fields = [
            'date_of_birth', 'gender', 'current_weight', 
            'current_height', 'activeness_level', 'goal'
        ]
        missing_fields = [
            field for field in required_fields 
            if not getattr(user, field, None)
        ]
        
        if missing_fields:
            return Response(
                {'error': f'Missing required fields: {", ".join(missing_fields)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Initialize calculator
            calculator = DailyLimitsCalculator()
            
            # Calculate personalized limits from user profile
            ingredients_summary = calculator.calculate_from_user(user)
            
            # Create or update DailyIngredientsLimit record
            daily_limits, created = DailyIngredientsLimit.objects.update_or_create(
                user=user,
                defaults={
                    'ingredients_summary': ingredients_summary
                }
            )
            
            # Serialize and return
            serializer = DailyIngredientsLimitSerializer(daily_limits)
            
            response_message = (
                "Daily limits generated successfully" 
                if created 
                else "Daily limits updated successfully"
            )
            
            return Response(
                {
                    'message': response_message,
                    'data': serializer.data
                },
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
            )
        
        except ValueError as e:
            logger.warning(f"Validation error for user {user.id}: {str(e)}")
            return Response(
                {'error': f'Invalid user data: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            logger.error(f"Error generating daily limits for user {user.id}: {str(e)}")
            return Response(
                {'error': 'Failed to generate daily limits. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@extend_schema(
    tags=['Daily Limit Calculation'],
    summary='Get Current Daily Limits',
    description='Retrieve current daily ingredient limits for authenticated user',
)
class RetrieveDailyLimitsView(APIView):
    """
    GET /api/daily-limits/
    
    Retrieves current daily ingredient limits for authenticated user.
    Fast lookup from database (single OneToOne query).
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current daily limits for user"""
        user = request.user
        
        try:
            daily_limits = DailyIngredientsLimit.objects.get(user=user)
            serializer = DailyIngredientsLimitSerializer(daily_limits)
            
            return Response(
                {
                    'data': serializer.data,
                    'status': 'success'
                },
                status=status.HTTP_200_OK
            )
        
        except DailyIngredientsLimit.DoesNotExist:
            return Response(
                {
                    'error': 'Daily limits not found. Please generate them first.',
                    'action': 'POST /api/daily-limits/generate/'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        except Exception as e:
            logger.error(f"Error retrieving daily limits for user {user.id}: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve daily limits'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@extend_schema(
    tags=['Daily Limit Calculation'],
    summary='Get Detailed Limits Breakdown',
    description='Get detailed breakdown with quick access properties',
)
class DailyLimitsDetailView(APIView):
    """
    GET /api/daily-limits/details/
    
    Retrieves specific ingredient limit details.
    Includes convenience properties (calories_target, protein_target, etc).
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get detailed breakdown of limits"""
        user = request.user
        
        try:
            daily_limits = DailyIngredientsLimit.objects.get(user=user)
            
            # Build detailed response
            response_data = {
                'id': str(daily_limits.id),
                'user_id': str(user.id),
                'created_at': daily_limits.created_at.isoformat(),
                'updated_at': daily_limits.updated_at.isoformat(),
                'quick_access': {
                    'calories_target': daily_limits.calories_target,
                    'protein_target': daily_limits.protein_target,
                    'fat_target': daily_limits.fat_target,
                    'carbs_target': daily_limits.carbs_target,
                    'sodium_target': daily_limits.sodium_target,
                    'fiber_target': daily_limits.fiber_target,
                },
                'all_ingredients': daily_limits.ingredients_summary,
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        except DailyIngredientsLimit.DoesNotExist:
            return Response(
                {'error': 'Daily limits not found'},
                status=status.HTTP_404_NOT_FOUND
            )

@extend_schema(
    tags=['Daily Limit Calculation'],
    summary='Get Specific Ingredient',
    description='Get limit for specific ingredient by name',
)
class GetSpecificIngredientView(APIView):
    """
    GET /api/daily-limits/ingredient/?name=protein
    
    Get limit for specific ingredient by name.
    Useful for dashboard cards showing individual nutrients.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get specific ingredient limit"""
        user = request.user
        ingredient_name = request.query_params.get('name')
        
        if not ingredient_name:
            return Response(
                {'error': 'Missing query parameter: name'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            daily_limits = DailyIngredientsLimit.objects.get(user=user)
            ingredient = daily_limits.get_ingredient(ingredient_name)
            
            if not ingredient:
                return Response(
                    {'error': f'Ingredient "{ingredient_name}" not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(
                {
                    'ingredient': ingredient,
                    'consumed_today': 0,
                    'remaining': ingredient['daily_norm'],
                },
                status=status.HTTP_200_OK
            )
        
        except DailyIngredientsLimit.DoesNotExist:
            return Response(
                {'error': 'Daily limits not found'},
                status=status.HTTP_404_NOT_FOUND
            )

@extend_schema(
    tags=['Daily Limit Calculation'],
    summary='Validate Daily Limits',
    description='Check if current limits are valid (debug endpoint)',
)
class ValidateDailyLimitsView(APIView):
    """
    GET /api/daily-limits/validate/
    
    Check if user's current limits are valid (have correct structure).
    Debug endpoint for testing.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Validate user's daily limits structure"""
        user = request.user
        
        try:
            daily_limits = DailyIngredientsLimit.objects.get(user=user)
            
            return Response(
                {
                    'is_valid': daily_limits.is_valid,
                    'ingredients_count': len(daily_limits.ingredients_summary),
                    'has_calories': daily_limits.calories_target is not None,
                    'has_protein': daily_limits.protein_target is not None,
                    'ingredients_list': [
                        ing['name'] for ing in daily_limits.ingredients_summary
                    ]
                },
                status=status.HTTP_200_OK
            )
        
        except DailyIngredientsLimit.DoesNotExist:
            return Response(
                {'error': 'Daily limits not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class QuickAccessView(APIView):
    """
    GET /api/daily-limits/quick-access/
    
    Get quick access to main macronutrients only.
    Lightweight endpoint for fast dashboard loading.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get quick access macros"""
        user = request.user
        
        try:
            daily_limits = DailyIngredientsLimit.objects.get(user=user)
            serializer = QuickAccessLimitsSerializer(daily_limits)
            
            return Response(
                {
                    'data': serializer.data,
                    'status': 'success'
                },
                status=status.HTTP_200_OK
            )
        
        except DailyIngredientsLimit.DoesNotExist:
            return Response(
                {'error': 'Daily limits not found'},
                status=status.HTTP_404_NOT_FOUND
            )