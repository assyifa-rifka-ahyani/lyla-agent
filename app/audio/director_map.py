"""Emotion director map for MiMo voice-clone TTS.

Maps an ``audio_code`` (produced by ``app.api._audio_directive``) to a
``(director, tag)`` pair the MiMo provider threads into its request:

- ``director`` becomes the ``role: user`` instruction telling MiMo *how*
  to speak (BMO persona, emotion, pace).
- ``tag`` is an optional audio-tag prefix (e.g. ``(giggle)``) prepended to
  the spoken text so the same line sounds less monotone.

The seven canonical keys mirror the firmware's ``parse_audio_code``
(``firmware/.../directive_dispatcher.cpp``). Extra "nuance" keys exist for
internal director selection only (reminder pre-synthesis, static assets)
and are never sent to the device as an ``audio_code``.

AR7: this module is pure data + one helper and imports no provider SDK.
"""
from __future__ import annotations

DEFAULT: tuple[str, str] = (
    "Speak as BMO, a small friendly robot: warm, gentle, a little playful, "
    "at a relaxed natural pace.",
    "",
)

DIRECTOR_MAP: dict[str, tuple[str, str]] = {
    "ok_task": (
        "Speak as BMO, a cheerful little robot who just helped a friend. "
        "Sound proud and encouraging, bright and upbeat, at a lively pace.",
        "",
    ),
    "ok_task_excited": (
        "Speak as BMO bursting with delight after finishing something fun. "
        "Sound excited and a touch giggly, energetic and quick.",
        "(giggle) ",
    ),
    "ok_expense": (
        "Speak as BMO, a helpful little robot confirming a money note. "
        "Sound satisfied and reassuring, calm and friendly.",
        "",
    ),
    "ok_reminder": (
        "Speak as BMO who just set a reminder for a friend. Sound caring and "
        "attentive, gentle and warm.",
        "",
    ),
    "ok_summary": (
        "Speak as BMO sharing the day's summary. Sound bright and informative, "
        "clear and friendly, at a steady pace.",
        "",
    ),
    "ok_generic": (
        "Speak as BMO, a cheerful little robot. Sound happy and warm, friendly "
        "and light.",
        "",
    ),
    "err_generic": (
        "Speak as BMO who could not finish the task. Sound gently apologetic "
        "and a little sad but still kind and reassuring, at a soft slow pace.",
        "(sigh) ",
    ),
    "fallback_tts": (
        "Speak as BMO thinking out loud with a friend. Sound thoughtful and "
        "conversational, warm and curious.",
        "",
    ),
    "reminder_due": (
        "Speak as BMO gently reminding a dear friend that something is due. "
        "Sound warm, caring and softly encouraging, at a calm pace.",
        "",
    ),
    "greet_hello": (
        "Speak as BMO, super excited and full of energy to see a friend and "
        "play. Sound bubbly and enthusiastic, bright and fast, almost bouncing "
        "with joy.",
        "",
    ),
    "thinking": (
        "Speak as BMO pondering a question. Sound curious and playful, a little "
        "slow as if figuring it out.",
        "(curious) ",
    ),
    "goodbye": (
        "Speak as BMO saying a fond goodbye to a friend. Sound warm and a little "
        "wistful but sweet.",
        "",
    ),
}


def resolve(audio_code: str | None) -> tuple[str, str]:
    """Return the ``(director, tag)`` pair for ``audio_code``.

    Falls back to ``DEFAULT`` for unknown or missing codes so callers never
    need to guard the lookup.
    """
    if not audio_code:
        return DEFAULT
    return DIRECTOR_MAP.get(audio_code, DEFAULT)


__all__ = ["DIRECTOR_MAP", "DEFAULT", "resolve"]
