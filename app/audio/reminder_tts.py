"""TTS synthesis pipeline for reminders (Phase 14).

Hybrid policy:
- ``synthesize_for_reminder`` is called fire-and-forget at create time
  and again from the scheduler tick if the reminder still has
  ``tts_status != "ready"`` when it is due.
- Cache key is ``reminder:{reminder_id}`` so the GET endpoint can serve
  bytes without hitting the provider again.
- On failure the reminder transitions to ``tts_status == "failed"``;
  the scheduler tick falls back to ``ok_reminder`` (canned WAV on SD)
  so the device still plays *something*.

The provider call is sync because ``app/audio/tts.py`` is sync;
callers that want fire-and-forget wrap this in a thread.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.audio._seam import ConfigurationError
from app.audio.tts import synthesize_text
from app.audio.tts_cache import tts_cache
from app.services import reminder_service
from app.utils.timezone import now_utc


log = logging.getLogger(__name__)


def cache_key(reminder_id: str) -> str:
    return f"reminder:{reminder_id}"


def synthesize_for_reminder(
    db: Session,
    reminder_id: str,
    *,
    force: bool = False,
) -> bool:
    """Synthesize TTS for a reminder and cache the bytes.

    Returns ``True`` when bytes are in cache after this call (either
    freshly synthesized or already-cached when ``force=False``), and
    ``False`` when synthesis failed. Updates the reminder's
    ``tts_status`` either way so the dashboard and tick can observe
    progress.
    """
    from app.models.reminder import Reminder

    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).one_or_none()
    if reminder is None:
        return False

    key = cache_key(reminder_id)
    if not force and reminder.tts_status == "ready" and tts_cache.has(key):
        return True

    reminder_service.update_reminder_tts_state(
        db, reminder_id, tts_status="pending"
    )

    try:
        result = synthesize_text(reminder.title)
    except ConfigurationError as exc:
        log.warning("reminder TTS synth config error rid=%s err=%s", reminder_id, exc)
        reminder_service.update_reminder_tts_state(
            db, reminder_id, tts_status="failed"
        )
        return False
    except Exception as exc:
        log.warning("reminder TTS synth failed rid=%s err=%s", reminder_id, exc)
        reminder_service.update_reminder_tts_state(
            db, reminder_id, tts_status="failed"
        )
        return False

    tts_cache.put(key, result.audio_bytes, result.content_type)
    reminder_service.update_reminder_tts_state(
        db,
        reminder_id,
        tts_status="ready",
        tts_audio_id=key,
        tts_synthesized_at=now_utc(),
    )
    return True


__all__ = ["cache_key", "synthesize_for_reminder"]
