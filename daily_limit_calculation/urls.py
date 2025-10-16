# daily_limit_calculation/urls.py

from django.urls import path
from .views import (
    GenerateDailyLimitsView,
    RetrieveDailyLimitsView,
    DailyLimitsDetailView,
    GetSpecificIngredientView,
    ValidateDailyLimitsView,
    QuickAccessView,
)

app_name = 'daily_limit_calculation'

urlpatterns = [
    # Generate/create daily limits from user profile
    path(
        'generate/',
        GenerateDailyLimitsView.as_view(),
        name='generate_daily_limits'
    ),
    
    # Get current daily limits (all 24 ingredients)
    path(
        '',
        RetrieveDailyLimitsView.as_view(),
        name='retrieve_daily_limits'
    ),
    
    # Get detailed view with convenience properties
    path(
        'details/',
        DailyLimitsDetailView.as_view(),
        name='daily_limits_details'
    ),
    
    # Get specific ingredient by name
    # Usage: GET /api/daily-limits/ingredient/?name=sodium
    path(
        'ingredient/',
        GetSpecificIngredientView.as_view(),
        name='get_ingredient'
    ),
    
    # Validate current limits (debug endpoint)
    path(
        'validate/',
        ValidateDailyLimitsView.as_view(),
        name='validate_daily_limits'
    ),
    
    # Quick access to main macros only
    path(
        'quick-access/',
        QuickAccessView.as_view(),
        name='quick_access'
    ),
]