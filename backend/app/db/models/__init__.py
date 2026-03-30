# Import all ORM models here so SQLAlchemy's metadata discovers them
# for table creation and future Alembic migrations.

from app.db.models.conversation import Conversation, Message  # noqa: F401
from app.db.models.event import EventLog  # noqa: F401
from app.db.models.summary import ConversationSummary  # noqa: F401
from app.db.models.background_job import BackgroundJob  # noqa: F401
from app.db.models.escalation import EscalationCase, EscalationNote  # noqa: F401
