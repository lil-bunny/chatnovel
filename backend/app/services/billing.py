from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Subscription


def is_premium(db: Session, user_id: str) -> bool:
    sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id, Subscription.status == "active")
        .order_by(Subscription.renewal_at.desc())
        .first()
    )
    if not sub:
        return False
    if sub.renewal_at and sub.renewal_at < datetime.now(timezone.utc):
        sub.status = "expired"
        return False
    return True


def activate_stub(db: Session, user_id: str, product_id: str = "premium_monthly") -> Subscription:
    sub = Subscription(
        user_id=user_id,
        provider="stub",
        product_id=product_id,
        status="active",
        renewal_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(sub)
    db.flush()
    return sub
