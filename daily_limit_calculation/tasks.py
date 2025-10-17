# daily_limit_calculation/tasks.py

import logging
from celery import shared_task
from django.contrib.auth import get_user_model

from .models import DailyIngredientsLimit
from .services import DailyLimitsCalculator

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def calculate_daily_limits_async(self, user_id):
    """
    Asynchronous task to calculate daily limits.
    
    Use this when generating limits from API so it doesn't block the request.
    
    Args:
        user_id: UUID of the user
    
    Retries:
        - On failure, retries up to 3 times with exponential backoff
    
    Example:
        # In view:
        calculate_daily_limits_async.delay(user.id)
        return Response({'message': 'Generating daily limits...'}, status=202)
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Initialize calculator
        calculator = DailyLimitsCalculator()
        
        # Calculate limits from user profile
        ingredients_summary = calculator.calculate_from_user(user)
        
        # Save to database
        daily_limits, created = DailyIngredientsLimit.objects.update_or_create(
            user=user,
            defaults={'ingredients_summary': ingredients_summary}
        )
        
        action = "created" if created else "updated"
        logger.info(f"Daily limits {action} for user {user.email}")
        
        return {
            'success': True,
            'user_id': str(user_id),
            'action': action,
            'ingredients_count': len(ingredients_summary)
        }
    
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'success': False, 'error': 'User not found'}
    
    except ValueError as e:
        logger.warning(f"Validation error for user {user_id}: {str(e)}")
        return {'success': False, 'error': f'Validation error: {str(e)}'}
    
    except Exception as e:
        logger.error(f"Error calculating limits for user {user_id}: {str(e)}")
        
        # Retry with exponential backoff
        retry_in = 2 ** self.request.retries  # 2, 4, 8 seconds
        raise self.retry(exc=e, countdown=retry_in)


@shared_task
def recalculate_all_user_limits():
    """
    Periodic task to recalculate limits for all users.
    
    Schedule this with Celery Beat (e.g., weekly):
    
    CELERY_BEAT_SCHEDULE = {
        'recalculate-daily-limits': {
            'task': 'daily_limit_calculation.tasks.recalculate_all_user_limits',
            'schedule': crontab(hour=2, minute=0, day_of_week=0),  # Weekly, Sunday 2 AM
        },
    }
    """
    users = User.objects.filter(profile_completed=True)
    
    for user in users:
        try:
            calculate_daily_limits_async.delay(user.id)
            logger.info(f"Queued limit recalculation for user {user.email}")
        except Exception as e:
            logger.error(f"Failed to queue recalculation for {user.email}: {str(e)}")
    
    return f"Queued recalculation for {users.count()} users"


@shared_task
def calculate_limits_for_new_users_batch(user_ids):
    """
    Calculate limits for multiple users at once.
    Useful when batch processing new user signups.
    
    Args:
        user_ids: List of user IDs
    
    Example:
        # After signup process:
        new_user_ids = [str(user.id) for user in newly_created_users]
        calculate_limits_for_new_users_batch.delay(new_user_ids)
    """
    results = []
    
    for user_id in user_ids:
        try:
            result = calculate_daily_limits_async.delay(user_id)
            results.append({'user_id': user_id, 'status': 'queued'})
        except Exception as e:
            logger.error(f"Failed to queue limit calculation for user {user_id}: {str(e)}")
            results.append({'user_id': user_id, 'status': 'failed', 'error': str(e)})
    
    return results