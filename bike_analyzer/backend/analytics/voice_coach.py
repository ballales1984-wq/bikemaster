"""Voice Coach — live audio guidance logic for BikeMaster (Pillar 3).

The synthesis (TTS) and recognition (STT) themselves run on the device via the
Web Speech API (frontend) or native TTS (Capacitor mobile). This module provides
the *decision* layer that the device calls:

- :class:`VoiceCommandParser` — understands spoken commands
  ("Stop", "Pausa", "Come sto andando?").
- :class:`VoiceCoach` — decides when a spoken message is allowed during a ride,
  simplifies the text to <=2 concepts, enforces the minimum gap, and produces
  audio cues ("Inizia riscaldamento", "5 minuti rimanenti").

Priority order (per product logic): safety > recovery > performance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .proactive import MessageComposer, SmartTiming


class VoiceCommand(StrEnum):
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"
    STATUS = "status"
    UNKNOWN = "unknown"


_VOICE_INTENT: dict[str, list[str]] = {
    VoiceCommand.STOP.value: ["stop", "ferma", "fermati", "stoppa"],
    VoiceCommand.PAUSE.value: ["pausa", "pause", "ferma un attimo"],
    VoiceCommand.RESUME.value: ["riprendi", "resume", "continua", "via"],
    VoiceCommand.STATUS.value: [
        "come sto andando",
        "come va",
        "come stai andando",
        "how am i doing",
        "status",
        "come sto",
    ],
}


@dataclass
class ParsedCommand:
    command: VoiceCommand
    raw: str
    language: str


class VoiceCommandParser:
    """Parses spoken/recognized text into a :class:`VoiceCommand`."""

    @staticmethod
    def parse(text: str, language: str = "it") -> ParsedCommand:
        normalized = re.sub(r"[^\w\s]", " ", (text or "").lower()).strip()
        for command, phrases in _VOICE_INTENT.items():
            for phrase in phrases:
                if phrase in normalized:
                    return ParsedCommand(VoiceCommand(command), text, language)
        return ParsedCommand(VoiceCommand.UNKNOWN, text, language)


class VoiceCoach:
    """Decides spoken output during a ride and produces audio cues."""

    def __init__(self, language: str = "it", last_spoken_at: float | None = None):
        self.language = language if language in ("it", "en") else "it"
        self.last_spoken_at = last_spoken_at
        self.composer = MessageComposer(self.language)

    def can_speak(self, intensity_zone: int | None, now_ts: float | None = None) -> tuple[bool, str]:
        """Whether a voice message is allowed now.

        Rules:
        - Never speak during Z4/Z5 unless safety (handled by caller).
        - Minimum 5-minute gap between voice messages.
        """
        if intensity_zone is not None and intensity_zone >= 4:
            return False, "high intensity (Z4/Z5)"
        if now_ts is not None and self.last_spoken_at is not None:
            gap = now_ts - self.last_spoken_at
            if gap < SmartTiming.min_voice_gap_seconds():
                return False, "voice gap not elapsed"
        return True, "ok"

    def speak_message(
        self,
        category: str,
        template_key: str,
        variables: dict[str, Any] | None = None,
        intensity_zone: int | None = None,
        now_ts: float | None = None,
    ) -> str | None:
        """Return the spoken text, or None if it must be suppressed now."""
        allowed, _why = self.can_speak(intensity_zone, now_ts)
        if not allowed:
            return None
        message, tts_text = self.composer.compose(category, template_key, variables)
        if now_ts is not None:
            self.last_spoken_at = now_ts
        return tts_text or message

    def cue(self, cue_key: str, variables: dict[str, Any] | None = None) -> str:
        """Produce a short audio cue (warm-up, countdown, etc.)."""
        lib = _AUDIO_CUES[self.language]
        text = lib.get(cue_key, lib.get("default", cue_key))
        try:
            return text.format(**(variables or {}))
        except (KeyError, IndexError, ValueError):
            return text

    @staticmethod
    def status_line(avg_power: float | None, zone: int | None, hr: int | None) -> str:
        lang = VoiceCoach.language if hasattr(VoiceCoach, "language") else "it"
        if lang == "en":
            parts = []
            if avg_power is not None:
                parts.append(f"average power {int(avg_power)} watts")
            if zone is not None:
                parts.append(f"zone {zone}")
            if hr is not None:
                parts.append(f"heart rate {hr}")
            return "You are doing " + (", ".join(parts) if parts else "well") + "."
        parts = []
        if avg_power is not None:
            parts.append(f"potenza media {int(avg_power)} watt")
        if zone is not None:
            parts.append(f"zona {zone}")
        if hr is not None:
            parts.append(f"frequenza cardiaca {hr}")
        return "Stai andando " + (", ".join(parts) if parts else "bene") + "."


_AUDIO_CUES: dict[str, dict[str, str]] = {
    "it": {
        "warmup": "Inizia riscaldamento",
        "cooldown": "Inizia defaticamento",
        "five_min_left": "Mancano 5 minuti",
        "one_km_left": "Manca 1 chilometro",
        "push": "Dai una spinta",
        "recover": "Recupera ora",
        "default": "Continua",
    },
    "en": {
        "warmup": "Start warm-up",
        "cooldown": "Start cool-down",
        "five_min_left": "5 minutes remaining",
        "one_km_left": "1 kilometer remaining",
        "push": "Push now",
        "recover": "Recover now",
        "default": "Keep going",
    },
}


__all__ = [
    "VoiceCommand",
    "VoiceCommandParser",
    "ParsedCommand",
    "VoiceCoach",
]
