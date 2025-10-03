import random
import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import CodeModel
import logging
from requests.auth import HTTPBasicAuth
import requests

logger = logging.getLogger(__name__)


def generate_sms_code() -> str:
    # code = str(random.randint(100000, 999999))
    code = str(123456)
    print(f"🔐 Generated SMS Code: {code}")
    return code


def send_sms_pass(phone: str, code: str) -> bool:
    """
    Pass function for sending SMS
    In production, this would integrate with SMS providers like Twilio, AWS SNS, etc.
    """
    request_url = "https://send.smsxabar.uz/broker-api/send"
    username = 'tasty'
    password = "i$*1R%=B@i3b"
    auth = HTTPBasicAuth(username, password)
    try:
        request_data = {
            "messages": [
                {
                    "recipient": phone,
                    "message-id": random.randint(111111111, 999999999),
                    "sms": {
                        "originator": '3700',
                        "content": {
                            "text": f"Your code is {code}",
                        },
                    },
                }
            ]
        }
        response = requests.post(
            request_url,
            auth=auth,
            json=request_data,
            timeout=5
        )
        print(response.content)
        if response.ok:
            return True
        else:
            return False

    except Exception as e:
        logger.error(f"Failed to send SMS to {phone}: {str(e)}")
        return False


async def create_sms_code(db: AsyncSession, phone: str) -> tuple[str, int]:
    try:
        code = generate_sms_code()
        session_id = uuid.uuid4()
        expires_at = datetime.utcnow() + timedelta(minutes=2)
        expires_in = 120

        code_record = CodeModel(
            code=code,
            session=session_id,
            expires_at=expires_at
        )

        db.add(code_record)
        await db.commit()
        await db.refresh(code_record)
        sms_sent = send_sms_pass(phone, code)

        if not sms_sent:
            logger.error(f"Failed to send SMS to {phone}")

        return str(session_id), expires_in

    except Exception as e:
        logger.error(f"Error creating SMS code: {str(e)}")
        await db.rollback()
        raise e


async def verify_sms_code(db: AsyncSession, session: str, code: str, phone: str) -> tuple[bool, str | None]:
    try:
        result = await db.execute(
            select(CodeModel).where(
                CodeModel.session == session,
                CodeModel.code == code,
                CodeModel.expires_at > datetime.utcnow()
            )
        )

        code_record = result.scalar_one_or_none()

        if code_record:
            await db.delete(code_record)
            await db.commit()
            return True, session

        return False, None

    except Exception as e:
        logger.error(f"Error verifying SMS code: {str(e)}")
        return False, None
