"""Task service: business logic for academic tasks.

All functions take a SQLAlchemy ``Session`` and primitive/Python objects.
They never depend on FastAPI, agent frameworks, or formatting concerns.

Validation order for ``create_task`` (per design):
    1. user exists
    2. title is non-blank
    3. ``deadline_at`` and ``reminder_at`` are aware datetimes (when supplied)
    4. ``reminder_at`` is not earlier than UTC Now

When ``reminder_at`` is supplied, a linked ``Reminder`` row is persisted in
the same commit so that the (task, reminder) pair is atomic.

Default reminder policy (Phase 14): when the caller omits ``reminder_at``
and ``auto_reminder`` is True (the agent's default code path), the service
materialises one of:
    - one hour before ``deadline_at`` if a deadline is given AND that
      moment is still in the future
    - one hour from ``now_utc()`` otherwise

This makes "ingatkan ada tugas X" produce a Task with a usable reminder
without forcing the agent to guess a time.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.constants import ReminderStatus, TaskStatus
from app.models.reminder import Reminder
from app.models.task import Task
from app.models.user import User
from app.services.exceptions import (
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.utils.timezone import now_utc


def _is_aware(dt: datetime) -> bool:
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


def _default_reminder_at(deadline_at: Optional[datetime]) -> datetime:
    """Pick a default ``remind_at`` for a task without explicit reminder.

    Returns one hour before ``deadline_at`` when that is still in the
    future; falls back to one hour from now otherwise.
    """
    now = now_utc()
    if deadline_at is not None and _is_aware(deadline_at):
        candidate = deadline_at - timedelta(hours=1)
        if candidate > now:
            return candidate
    return now + timedelta(hours=1)


def create_task(
    db: Session,
    user_id: str,
    title: str,
    course: Optional[str] = None,
    deadline_at: Optional[datetime] = None,
    reminder_at: Optional[datetime] = None,
    priority: Optional[str] = None,
    auto_reminder: bool = False,
) -> Task:
    """Persist a new ``Task`` and (optionally) a linked ``Reminder``.

    Returns the created ``Task``. Raises ``NotFoundError`` if ``user_id`` is
    unknown, or ``ValidationError`` when input fails validation. Persists no
    rows when validation fails.

    When ``reminder_at`` is None and ``auto_reminder`` is True, applies
    the default reminder policy documented at module level. Pass
    ``auto_reminder=False`` (e.g. from migration tools) to opt out.
    """
    user = db.query(User).filter(User.id == user_id).one_or_none()
    if user is None:
        raise NotFoundError(f"User {user_id!r} not found")

    if not isinstance(title, str) or not title.strip():
        raise ValidationError("Title must be a non-blank string")

    if deadline_at is not None:
        if not isinstance(deadline_at, datetime) or not _is_aware(deadline_at):
            raise ValidationError("deadline_at must be a timezone-aware datetime")
    if reminder_at is not None:
        if not isinstance(reminder_at, datetime) or not _is_aware(reminder_at):
            raise ValidationError("reminder_at must be a timezone-aware datetime")

    if reminder_at is None and auto_reminder:
        reminder_at = _default_reminder_at(deadline_at)

    if reminder_at is not None and reminder_at < now_utc():
        raise ValidationError("reminder_at must not be earlier than now")

    task = Task(
        user_id=user_id,
        title=title,
        course=course,
        deadline_at=deadline_at,
        reminder_at=reminder_at,
        priority=priority,
        status=TaskStatus.PENDING,
    )
    db.add(task)

    if reminder_at is not None:
        reminder = Reminder(
            user_id=user_id,
            task=task,
            title=title,
            remind_at=reminder_at,
            status=ReminderStatus.SCHEDULED,
        )
        db.add(reminder)

    db.commit()
    db.refresh(task)
    return task


def list_tasks(
    db: Session,
    user_id: str,
    status: Optional[str] = None,
) -> list[Task]:
    """Return tasks owned by ``user_id``, optionally filtered by ``status``."""
    query = db.query(Task).filter(Task.user_id == user_id)
    if status is not None:
        query = query.filter(Task.status == status)
    return query.all()


def mark_task_done(
    db: Session,
    user_id: str,
    task_id: str,
) -> Task:
    """Mark a task as done.

    - ``NotFoundError`` if the task does not exist.
    - ``PermissionDeniedError`` if the task exists but belongs to another user.
    """
    task = db.query(Task).filter(Task.id == task_id).one_or_none()
    if task is None:
        raise NotFoundError(f"Task {task_id!r} not found")
    if task.user_id != user_id:
        raise PermissionDeniedError(
            f"Task {task_id!r} does not belong to user {user_id!r}"
        )

    task.status = TaskStatus.DONE
    db.commit()
    db.refresh(task)
    return task


# Fields that ``update_task`` is allowed to patch. ``user_id`` is intentionally
# excluded so a task cannot change owner.
_UPDATABLE_FIELDS = frozenset(
    {"status", "title", "course", "deadline_at", "reminder_at", "priority"}
)


def update_task(db: Session, task_id: str, **patch) -> Task:
    """Apply a partial update to a ``Task`` row.

    Only fields with non-``None`` values are applied; keys outside
    :data:`_UPDATABLE_FIELDS` (e.g. ``user_id``) are silently ignored so
    ownership cannot be changed.

    Validation rules mirror :func:`create_task`:
        * ``title`` must be a non-blank string when supplied.
        * ``deadline_at`` and ``reminder_at`` must be timezone-aware
          datetimes when supplied.
        * ``reminder_at`` must not be earlier than UTC Now when supplied.

    Raises ``NotFoundError`` if no task with ``task_id`` exists, or
    ``ValidationError`` when input fails validation. No row is modified
    when validation fails.
    """
    task = db.query(Task).filter(Task.id == task_id).one_or_none()
    if task is None:
        raise NotFoundError(f"Task {task_id!r} not found")

    # Drop unknown keys and ``None`` values up front so validation/apply
    # operate on the same dict.
    effective = {
        key: value
        for key, value in patch.items()
        if key in _UPDATABLE_FIELDS and value is not None
    }

    if "title" in effective:
        title = effective["title"]
        if not isinstance(title, str) or not title.strip():
            raise ValidationError("Title must be a non-blank string")
    if "deadline_at" in effective:
        deadline_at = effective["deadline_at"]
        if not isinstance(deadline_at, datetime) or not _is_aware(deadline_at):
            raise ValidationError("deadline_at must be a timezone-aware datetime")
    if "reminder_at" in effective:
        reminder_at = effective["reminder_at"]
        if not isinstance(reminder_at, datetime) or not _is_aware(reminder_at):
            raise ValidationError("reminder_at must be a timezone-aware datetime")
        if reminder_at < now_utc():
            raise ValidationError("reminder_at must not be earlier than now")

    for key, value in effective.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task_id: str) -> None:
    """Delete a ``Task`` row by id.

    Raises ``NotFoundError`` if no task with ``task_id`` exists. The row
    is removed in a single transaction.
    """
    task = db.query(Task).filter(Task.id == task_id).one_or_none()
    if task is None:
        raise NotFoundError(f"Task {task_id!r} not found")
    db.delete(task)
    db.commit()
