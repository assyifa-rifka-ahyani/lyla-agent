"""Reminder Scheduler tick.

`reminder_tick` is a pure function that performs one Scheduler Tick:

1. Open a DB session via the supplied `db_factory`.
2. Fetch all Due Reminders via `reminder_service.list_due_reminders`.
3. For each reminder, route by `channel`:
   - `"device"` or `"both"` → resolve the user's first `Device` and call
     `device_service.queue_device_command(...)`.
   - `"whatsapp"` or `"both"` → call the injected `whatsapp_send`.
4. If every dispatch call returns without raising, transition the reminder
   to ``SENT`` via `reminder_service.mark_reminder_sent`.
5. If any dispatch call raises, catch the exception, transition the
   reminder to ``FAILED`` via `reminder_service.mark_reminder_failed`, and
   continue with the next Due Reminder within the same tick.
6. Special case (Req 8.7): when `channel == "device"` and the user has no
   associated `Device`, skip dispatch entirely and DO NOT transition the
   reminder's status. For `channel == "both"` with no device, skip the
   device dispatch but still attempt the WhatsApp leg.

Returns a counter dict: ``{"sent": int, "failed": int, "skipped": int}``.

This function intentionally takes a `db_factory` (not a `Session`) so the
APScheduler job and tests can both call it without sharing session state.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Callable, Optional

from app.audio import reminder_tts
from app.models.device import Device
from app.services import device_service, reminder_service
from app.utils.timezone import now_utc


COMMAND_EXPIRY_AFTER_DUE = timedelta(minutes=30)
DEVICE_ONLINE_WINDOW = timedelta(minutes=5)


def _build_reminder_command_payload(
    reminder, tts_ready: bool
) -> tuple[str, dict]:
    """Return ``(command_type, payload)`` for a due reminder.

    When ``tts_ready`` is True the device is told to fetch synthesized
    speech (Phase 11 ``fallback_tts`` shape) so playback can use the
    user's actual title. When False we fall back to the canned
    ``ok_reminder`` WAV that ships on the SD card so the device still
    plays *something* even if the TTS provider is down.
    """
    if tts_ready:
        directive = {
            "audio_code": "fallback_tts",
            "face": "neutral",
            "screen_text": reminder.title,
            "fetch_url": f"/reminders/{reminder.id}/tts",
        }
    else:
        directive = {
            "audio_code": "ok_reminder",
            "face": "neutral",
            "screen_text": reminder.title,
            "fetch_url": None,
        }
    return "play_reminder", {
        "reminder_id": reminder.id,
        "directive": directive,
    }


def _device_is_fresh(device: Device, now) -> bool:
    """Return True when device has heartbeat-ed within the online window."""
    last = device.last_seen_at
    if last is None:
        return False
    if last.tzinfo is None:
        from datetime import timezone as _tz

        last = last.replace(tzinfo=_tz.utc)
    return (now - last) < DEVICE_ONLINE_WINDOW


def reminder_tick(
    *,
    db_factory: Callable,
    whatsapp_send: Optional[Callable] = None,
) -> dict:
    """Run one Scheduler Tick and return a counter dict.

    Args:
        db_factory: Zero-argument callable that returns a fresh SQLAlchemy
            ``Session``. Typically `app.db.SessionLocal`.
        whatsapp_send: Optional callable accepting a ``Reminder`` and
            returning any value (return value is ignored). Defaults to
            ``app.integrations.whatsapp.whatsapp_send_stub``.

    Returns:
        ``{"sent": <int>, "failed": <int>, "skipped": <int>}``.
    """
    if whatsapp_send is None:
        from app.integrations.whatsapp import whatsapp_send_stub

        whatsapp_send = whatsapp_send_stub

    sent = 0
    failed = 0
    skipped = 0

    db = db_factory()
    try:
        due = reminder_service.list_due_reminders(db)
        now = now_utc()
        for reminder in due:
            try:
                channel = reminder.channel

                if channel in ("device", "both"):
                    user_devices = (
                        db.query(Device)
                        .filter(Device.user_id == reminder.user_id)
                        .filter(Device.last_seen_at.is_not(None))
                        .order_by(Device.last_seen_at.desc())
                        .all()
                    )
                    if user_devices:
                        device = user_devices[0]
                        if not _device_is_fresh(device, now):
                            reminder_service.update_reminder_failure_reason(
                                db, reminder.id, "device offline saat reminder jatuh tempo"
                            )
                            reminder_service.mark_reminder_failed(db, reminder.id)
                            failed += 1
                            continue

                        tts_ready = reminder_tts.synthesize_for_reminder(
                            db, reminder.id
                        )
                        command_type, payload = _build_reminder_command_payload(
                            reminder, tts_ready
                        )
                        remind_at = reminder.remind_at
                        if remind_at is not None and remind_at.tzinfo is None:
                            from datetime import timezone as _tz

                            remind_at = remind_at.replace(tzinfo=_tz.utc)
                        expires_at = max(remind_at, now) + COMMAND_EXPIRY_AFTER_DUE
                        device_service.queue_device_command(
                            db,
                            device.id,
                            command_type=command_type,
                            payload=payload,
                            expires_at=expires_at,
                        )
                    elif channel == "device":
                        skipped += 1
                        continue

                if channel in ("whatsapp", "both"):
                    whatsapp_send(reminder)

                reminder_service.mark_reminder_sent(db, reminder.id)
                sent += 1
            except Exception as exc:
                reminder_service.update_reminder_failure_reason(
                    db, reminder.id, f"dispatch error: {exc!s}"[:200]
                )
                reminder_service.mark_reminder_failed(db, reminder.id)
                failed += 1
    finally:
        db.close()

    return {"sent": sent, "failed": failed, "skipped": skipped}
