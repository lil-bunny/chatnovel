from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth_utils import current_user
from app.db import get_db
from app.models import User
from app.schemas import AnalyticsIn
from app.services import analytics

router = APIRouter(prefix="/v1/analytics", tags=["analytics"])


@router.post("/events")
def track(body: AnalyticsIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    analytics.emit(db, body.name, body.payload, user.id)
    return {"ok": True}
