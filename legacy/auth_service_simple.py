from typing import Optional, Dict, Any
from fastapi import HTTPException, status
import config
import logging
from jose import jwt, JWTError
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_google_token_simple(token: str) -> Dict[str, Any]:
    try:
        logger.info("Verifying Google token (simple mode)")
        unverified_claims = jwt.get_unverified_claims(token)

        email = unverified_claims.get('email')
        google_id = unverified_claims.get('sub')
        name = unverified_claims.get('name', '')
        given_name = unverified_claims.get('given_name', '')
        family_name = unverified_claims.get('family_name', '')
        picture = unverified_claims.get('picture', '')
        email_verified = unverified_claims.get('email_verified', False)
        iss = unverified_claims.get('iss', '')
        aud = unverified_claims.get('aud', '')
        exp = unverified_claims.get('exp', 0)
        
        if not email:
            raise ValueError("No email found in token")
        if not google_id:
            raise ValueError("No subject (Google ID) found in token")

        if iss not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError(f'Invalid issuer: {iss}')

        current_time = datetime.utcnow().timestamp()
        if exp and exp < current_time:
            raise ValueError("Token has expired")
            
        if config.GOOGLE_CLIENT_ID and config.GOOGLE_CLIENT_ID != "your-google-client-id-here":
            if aud != config.GOOGLE_CLIENT_ID:
                logger.warning(f"Token audience ({aud}) doesn't match configured client ID ({config.GOOGLE_CLIENT_ID})")
        
        logger.info(f"Token verified successfully for user: {email}")
        user_info = {
            'google_id': google_id,
            'email': email,
            'email_verified': email_verified,
            'name': name,
            'given_name': given_name,
            'family_name': family_name,
            'picture': picture,
        }
        
        return user_info
        
    except JWTError as e:
        logger.error(f"JWTError in token verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token format: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"ValueError in token verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in token verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token verification failed: {str(e)}"
        )
