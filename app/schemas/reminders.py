from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    task_id: Optional[str] = None
    title: str
    remind_at: datetime
    channel: str
    status: str
    created_at: Optional[datetime] = None
    tts_status: Optional[str] = None
