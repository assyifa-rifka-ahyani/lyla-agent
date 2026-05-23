from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api._auth_dependencies import require_device_token, require_session
from app.audio import reminder_tts
from app.audio.tts_cache import tts_cache
from app.db import get_db
from app.models.reminder import Reminder
from app.schemas.reminders import ReminderOut
from app.services import reminder_service
from app.services.exceptions import NotFoundError


router = APIRouter(tags=["Reminders"])


@router.get(
    "/reminders",
    response_model=list[ReminderOut],
    dependencies=[Depends(require_session)],
)
def list_reminders(
    user_id: str = Query(...),
    status_filter: str | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
) -> list[ReminderOut]:
    rows = reminder_service.list_reminders_for_user(
        db, user_id, status=status_filter
    )
    return [ReminderOut.model_validate(r) for r in rows]


@router.delete(
    "/reminders/{reminder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_session)],
)
def cancel_reminder(
    reminder_id: str,
    db: Session = Depends(get_db),
) -> None:
    try:
        reminder_service.mark_reminder_cancelled(db, reminder_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder tidak ditemukan",
        )


@router.get(
    "/reminders/{reminder_id}/tts",
    dependencies=[Depends(require_device_token)],
)
async def get_reminder_tts(
    reminder_id: str,
    db: Session = Depends(get_db),
) -> Response:
    key = reminder_tts.cache_key(reminder_id)
    entry = tts_cache.get(key)
    if entry is None:
        reminder = (
            db.query(Reminder).filter(Reminder.id == reminder_id).one_or_none()
        )
        if reminder is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reminder tidak ditemukan",
            )
        ok = reminder_tts.synthesize_for_reminder(db, reminder_id, force=True)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="TTS reminder tidak tersedia",
            )
        entry = tts_cache.get(key)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="TTS reminder tidak tersedia",
            )
    audio_bytes, content_type = entry
    return Response(content=audio_bytes, media_type=content_type)
