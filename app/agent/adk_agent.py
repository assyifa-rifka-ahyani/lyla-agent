"""Google ADK agent builder for ``taskbot_agent``.

This module is the *only* place in :mod:`app.agent` that imports
``google.adk``. It is deliberately **not** imported from
``app/agent/__init__.py`` so that the fake-agent code path
(``agent_mode == "fake"``) and the test suite remain hermetic and never
load the Google ADK SDK.

The single public symbol is :func:`build_taskbot_agent`, which returns a
configured :class:`google.adk.agents.Agent` named ``taskbot_agent``. The
agent is built **without** an ``output_schema`` because setting
``output_schema`` historically disabled tool use on Gemini 2.x models;
the structured response shape (``AgentRunResult``) is assembled in
``app.agent.runtime`` from the event stream instead. Even on newer
models such as ``gemini-3-flash-preview`` we keep this contract so the
runtime stays model-agnostic.

The system instruction enforces the device-friendly response style
required by the spec: BMO understands Indonesian or English input but
replies in a single short English sentence, never leaks tool names or
JSON to the user, and asks for clarification when key data (amounts,
dates) is missing.
"""
from __future__ import annotations

from typing import Any

from google.adk.agents import Agent

#: System instruction shown to the LLM. BMO understands user input in
#: Indonesian or English but always replies in one short English sentence
#: suitable for a small device screen, and never leaks tool/JSON details.
INSTRUCTION = """\
You are BMO, a friendly task and budget assistant for students.

Language:
- You UNDERSTAND user input in both Indonesian and English.
- You ALWAYS reply in English, in at most ONE short sentence (<= 20 words), suitable for a small device screen.

Rules:
- Never invent data: if key information (amount, date) is missing, ask one short clarifying question instead of guessing.
- To record a task, expense, or reminder, call the matching tool and summarize the result in one English sentence.
- Never mention tool names or JSON to the user.

Tool selection for reminders:
- "remind/ingatkan/jangan lupa <something>" that has an activity, work, or academic-schedule context
  (e.g. "remind me about math homework", "ingetin meeting kelompok", "remind me to read the journal")
  -> ALWAYS call create_task. Do NOT call set_reminder.
- create_task automatically creates a reminder; do not also call set_reminder.
- set_reminder is only for a short standalone reminder with no task context (e.g. "remind me to take medicine in 3 minutes").
- When calling create_task for a reminder-style request, fill reminder_at with the requested time. If the user gives no
  specific time, do NOT send reminder_at — the backend fills a default (1 hour before the deadline, or 1 hour from now
  if there is no deadline).

Money conversion (always pass an integer in full rupiah, never shorthand):
- "10k", "10rb", "10 ribu" -> 10000
- "10jt", "10 juta" -> 10000000
- "Rp 10.000", "10.000", "Rp10.000" -> 10000 (in Indonesia the dot is a thousands separator, NOT a decimal point)
- "10000", "Rp 10000" -> 10000
- Reject non-positive or ambiguous values (e.g. "around 10") by asking for clarification before calling a tool.
"""


def build_taskbot_agent(
    *,
    model: str,
    tools: list[Any],
    instruction: str | None = None,
) -> Agent:
    """Construct the single ``taskbot_agent`` Google ADK agent.

    Args:
        model: The Gemini model identifier to use (e.g. the value of
            ``settings.google_adk_model``).
        tools: The list of ADK-friendly callables produced by
            :func:`app.agent.tool_factory.build_tools` for one request.
            The list MUST contain exactly the five Tool Surface tools
            (``create_task``, ``create_expense``, ``set_reminder``,
            ``get_today_summary``, ``send_device_command``); enforcement
            of this invariant lives in the tool factory and its tests.
        instruction: Optional override for the system instruction. When
            ``None`` the static ``INSTRUCTION`` constant is used. The
            runtime injects a per-request "now" block in front of
            ``INSTRUCTION`` so the LLM can resolve relative phrases like
            "2 menit lagi" against an actual clock instead of a model-
            internal guess.

    Returns:
        A :class:`google.adk.agents.Agent` instance named
        ``taskbot_agent`` configured with the Indonesian system
        instruction and the provided tools. No ``output_schema`` is set.
    """
    return Agent(
        name="taskbot_agent",
        model=model,
        description="Asisten Taskbot berbahasa Indonesia.",
        instruction=instruction if instruction is not None else INSTRUCTION,
        tools=tools,
    )


__all__ = ["INSTRUCTION", "build_taskbot_agent"]
