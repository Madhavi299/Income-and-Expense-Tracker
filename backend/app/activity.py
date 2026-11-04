from sqlalchemy.orm import Session

from backend.app.models import ActivityLog


def record_activity(
    db: Session,
    action: str,
    actor_user_id: int | None = None,
    target_user_id: int | None = None,
    details: str | None = None,
) -> None:
    db.add(
        ActivityLog(
            action=action,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            details=details,
        )
    )
