from sqlalchemy.orm import Session

from app.models import AnalyticsEvent


def emit(db: Session, name: str, payload: dict | None = None, user_id: str | None = None) -> None:
    db.add(AnalyticsEvent(name=name, payload_json=payload or {}, user_id=user_id))
