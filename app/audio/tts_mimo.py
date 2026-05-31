"""MiMo V2.5 voice-clone TTS provider.

Implements the ``TtsProvider`` shape from ``app.audio._seam`` against
Xiaomi MiMo's OpenAI-compatible ``chat.completions`` endpoint. The BMO
persona voice is cloned from a local reference sample sent as a base64
data URI; emotion is steered by a ``director`` (``role: user``) line while
the spoken text (optionally prefixed with an audio ``tag``) is the
``role: assistant`` turn.

AR7: the ``openai`` SDK import is deferred to inside method bodies, mirroring
``tts_gemini.py`` and ``app.agent.runtime._run_real``. Nothing at module
load pulls a provider SDK. The voice sample is base64-encoded once at
construction and cached, never re-encoded per request.
"""
from __future__ import annotations

import base64
import io
import wave
from pathlib import Path

from app.audio._seam import ConfigurationError, SynthesisResult

_PCM_SAMPLE_RATE = 24000
_PCM_CHANNELS = 1
_PCM_SAMPLE_WIDTH = 2
_RIFF_MAGIC = b"RIFF"


def _wrap_pcm_to_wav(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(_PCM_CHANNELS)
        wf.setsampwidth(_PCM_SAMPLE_WIDTH)
        wf.setframerate(_PCM_SAMPLE_RATE)
        wf.writeframes(pcm)
    return buf.getvalue()


class MimoTtsProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        voice_sample_path: str,
    ) -> None:
        if not api_key:
            raise ConfigurationError(
                "MiMo TTS requires MIMO_API_KEY; set it in .env."
            )
        sample = Path(voice_sample_path)
        if not sample.is_file():
            raise ConfigurationError(
                f"MiMo voice sample not found at {voice_sample_path!r}; "
                "set MIMO_VOICE_SAMPLE_PATH to a valid mp3/wav (<=10MB)."
            )
        self._model = model
        self._base_url = base_url
        self._api_key = api_key
        voice_b64 = base64.b64encode(sample.read_bytes()).decode("ascii")
        self._voice_data_uri = f"data:audio/mpeg;base64,{voice_b64}"

    def synthesize(
        self,
        text: str,
        director: str | None = None,
        tag: str | None = None,
    ) -> SynthesisResult:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        spoken = (tag or "") + text
        completion = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "user", "content": director or ""},
                {"role": "assistant", "content": spoken},
            ],
            audio={"format": "wav", "voice": self._voice_data_uri},
        )

        try:
            message = completion.choices[0].message
            audio = message.audio
            encoded = audio["data"] if isinstance(audio, dict) else audio.data
        except (IndexError, AttributeError, KeyError, TypeError) as exc:
            raise RuntimeError(
                "MiMo TTS response did not contain audio data."
            ) from exc

        if not encoded:
            raise RuntimeError("MiMo TTS returned empty audio data.")

        raw = base64.b64decode(encoded)
        # Non-streaming mode returns a WAV container; if a bare PCM frame
        # comes back instead, wrap it so callers always get a RIFF header.
        audio_bytes = raw if raw[:4] == _RIFF_MAGIC else _wrap_pcm_to_wav(raw)

        return SynthesisResult(
            mode="mimo",
            content_type="audio/wav",
            audio_bytes=audio_bytes,
            text=text,
            metadata={
                "model": self._model,
                "director": director,
                "tag": tag,
                "sample_rate": _PCM_SAMPLE_RATE,
                "channels": _PCM_CHANNELS,
            },
        )


__all__ = ["MimoTtsProvider"]
