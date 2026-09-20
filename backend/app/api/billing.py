from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth_utils import current_user
from app.db import get_db
from app.models import User
from app.schemas import BillingMeOut
from app.services import analytics
from app.services.billing import activate_stub, is_premium

router = APIRouter(prefix="/v1/billing", tags=["billing"])


@router.get("/me", response_model=BillingMeOut)
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    premium = is_premium(db, user.id)
    return BillingMeOut(premium=premium, status="active" if premium else "none", product_id="premium_monthly" if premium else None)


@router.post("/checkout", response_model=BillingMeOut)
def checkout(user: User = Depends(current_user), db: Session = Depends(get_db)):
    analytics.emit(db, "trial_start", {"product_id": "premium_monthly"}, user.id)
    activate_stub(db, user.id)
    analytics.emit(db, "subscription_purchase", {"product_id": "premium_monthly"}, user.id)
    return me(user, db)


@router.post("/webhook")
def webhook():
    # Platform webhooks later. Stub acknowledges.
    return {"ok": True}
