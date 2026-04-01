from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.db import crud

logger = get_logger(__name__)


class NotifierService:
    async def send_notification(
        self,
        db: AsyncSession,
        user_id: str,
        case_id: str,
        channel: str = "email",
    ) -> None:
        metadata = {
            "available_channels": ["email", "whatsapp"],
            "delivery_mode": "stub",
            "message_template": "escalation_created",
        }
        await crud.create_notification_log(
            db,
            user_id=user_id,
            case_id=case_id,
            channel=channel,
            provider="stub",
            status="queued",
            metadata_json=metadata,
        )
        logger.info(
            "notification.stub.sent",
            extra={"user_id": user_id, "case_id": case_id, "channel": channel},
        )
        logger.info("User notified about escalation", extra={"user_id": user_id, "case_id": case_id})


notifier = NotifierService()
