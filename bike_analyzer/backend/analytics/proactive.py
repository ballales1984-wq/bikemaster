"""Proactive Assistant — notification & communication engine for BikeMaster.

Implements the decision layer that decides WHEN and HOW to intervene with the
athlete. The guiding principle ("intervenire meno, ma meglio") is enforced by:

- :class:`ContextEvaluator` — scores message importance (urgency/relevance/
  timeliness) against a minimum threshold.
- :class:`SmartTiming` — chooses the right moment, never interrupting high
  intensity work and respecting quiet hours and athlete preferences.
- :class:`MessageComposer` — generates clear, coach-style messages in IT/EN.
- :class:`NotificationRouter` — selects the channel (app/voice/dashboard/email)
  and decides whether/batched to deliver.

The services are framework-agnostic and only depend on plain dicts so they can
be reused by the FastAPI layer, the simulation engine (bm2) and the Tauri app.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

MIN_NOTIFY_SCORE = 3.0


class Channel(str, Enum):
    APP = "app"
    VOICE = "voice"
    DASHBOARD = "dashboard"
    EMAIL = "email"


class NotificationCategory(str, Enum):
    TRAINING = "training"
    RECOVERY = "recovery"
    PERFORMANCE = "performance"
    SAFETY = "safety"
    GOAL = "goal"


# Channel priority for safety situations is always forced to voice (live).
_CATEGORY_PRIORITY: dict[str, int] = {
    NotificationCategory.SAFETY.value: 1,
    NotificationCategory.RECOVERY.value: 2,
    NotificationCategory.PERFORMANCE.value: 3,
    NotificationCategory.TRAINING.value: 4,
    NotificationCategory.GOAL.value: 5,
}


@dataclass
class NotificationContext:
    """Aggregated context used to evaluate a candidate notification."""

    athlete_state: dict[str, Any] = field(default_factory=dict)
    plan: dict[str, Any] | None = None
    current_ride: dict[str, Any] | None = None
    weather: dict[str, Any] | None = None
    intensity_zone: int | None = None  # 0-5, current training zone
    now: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class NotificationScore:
    urgency: int
    relevance: int
    timeliness: int
    score: float
    should_notify: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class Notification:
    id: str
    category: str
    channel: str
    title: str
    message: str
    tts_text: str | None = None
    score: float = 0.0
    priority: int = 5
    language: str = "it"
    created_at: datetime | None = None


@dataclass
class NotificationPreferences:
    language: str = "it"
    quiet_hours_start: int = 23
    quiet_hours_end: int = 7
    max_background_per_ride: int = 2
    allow_voice_coach: bool = True
    allow_email_summary: bool = True
    paused: bool = False
    channel_priority: list[str] = field(
        default_factory=lambda: ["app", "voice", "dashboard", "email"]
    )
    respect_quiet_hours: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NotificationPreferences":
        allowed = {"app", "voice", "dashboard", "email"}
        chan = [c for c in data.get("channel_priority", []) if c in allowed]
        return cls(
            language=data.get("language", "it"),
            quiet_hours_start=int(data.get("quiet_hours_start", 23)),
            quiet_hours_end=int(data.get("quiet_hours_end", 7)),
            max_background_per_ride=int(data.get("max_background_per_ride", 2)),
            allow_voice_coach=bool(data.get("allow_voice_coach", True)),
            allow_email_summary=bool(data.get("allow_email_summary", True)),
            paused=bool(data.get("paused", False)),
            channel_priority=chan or ["app", "voice", "dashboard", "email"],
            respect_quiet_hours=bool(data.get("respect_quiet_hours", True)),
        )


class ContextEvaluator:
    """Scores the importance of a candidate notification.

    Each dimension is rated 1-5; the final score is the mean of the three.
    A message is only worth sending when ``score >= MIN_NOTIFY_SCORE``.
    """

    @staticmethod
    def evaluate(
        context: NotificationContext,
        *,
        category: str = NotificationCategory.TRAINING.value,
        signals: dict[str, Any] | None = None,
    ) -> NotificationScore:
        signals = signals or {}
        reasons: list[str] = []

        urgency = ContextEvaluator._urgency(context, category, signals, reasons)
        relevance = ContextEvaluator._relevance(context, category, signals, reasons)
        timeliness = ContextEvaluator._timeliness(context, category, signals, reasons)

        score = round((urgency + relevance + timeliness) / 3.0, 2)
        should_notify = score >= MIN_NOTIFY_SCORE or category == NotificationCategory.SAFETY.value

        if should_notify and category == NotificationCategory.SAFETY.value and score < MIN_NOTIFY_SCORE:
            reasons.append("safety: always notify regardless of score")
        return NotificationScore(
            urgency=urgency,
            relevance=relevance,
            timeliness=timeliness,
            score=score,
            should_notify=should_notify,
            reasons=reasons,
        )

    @staticmethod
    def _urgency(
        context: NotificationContext,
        category: str,
        signals: dict[str, Any],
        reasons: list[str],
    ) -> int:
        base = {
            NotificationCategory.SAFETY.value: 5,
            NotificationCategory.RECOVERY.value: 4,
            NotificationCategory.PERFORMANCE.value: 3,
            NotificationCategory.TRAINING.value: 3,
            NotificationCategory.GOAL.value: 2,
        }.get(category, 3)

        if signals.get("risk"):
            base = 5
            reasons.append("risk detected")
        if signals.get("insufficient_recovery"):
            base = max(base, 4)
            reasons.append("insufficient recovery")
        if signals.get("plan_changed"):
            base = max(base, 4)
        if signals.get("stopped_minutes", 0) >= 10:
            base = 5
            reasons.append("athlete stopped for a long time")
        return int(max(1, min(5, base)))

    @staticmethod
    def _relevance(
        context: NotificationContext,
        category: str,
        signals: dict[str, Any],
        reasons: list[str],
    ) -> int:
        # Personal relevance: tied to the athlete's own plan/state/goal.
        score = 3
        plan = context.plan or {}
        state = context.athlete_state or {}

        if category == NotificationCategory.GOAL.value and plan.get("goal_active"):
            score = 5
            reasons.append("linked to active goal")
        if category == NotificationCategory.RECOVERY.value and state.get("tsb", 0) < -15:
            score = 5
            reasons.append("freshness deficit")
        if category == NotificationCategory.TRAINING.value and plan.get("planned_today"):
            score = 4
            reasons.append("matches today's plan")
        if signals.get("already_known"):
            score = 1
            reasons.append("information already known")
        if signals.get("minor_stat"):
            score = 1
            reasons.append("minor statistic, not relevant")
        return int(max(1, min(5, score)))

    @staticmethod
    def _timeliness(
        context: NotificationContext,
        category: str,
        signals: dict[str, Any],
        reasons: list[str],
    ) -> int:
        score = 3
        if category == NotificationCategory.SAFETY.value:
            score = 5
            reasons.append("immediate safety")
        elif category == NotificationCategory.TRAINING.value:
            if (context.plan or {}).get("planned_today"):
                score = 5
                reasons.append("actionable today")
            elif (context.plan or {}).get("planned_soon"):
                score = 4
        elif category == NotificationCategory.RECOVERY.value:
            if (context.athlete_state or {}).get("tsb", 0) < -15:
                score = 5
                reasons.append("recovery needed now")
        if signals.get("stale"):
            score = 1
            reasons.append("stale information")
        return int(max(1, min(5, score)))


class SmartTiming:
    """Chooses the right moment to deliver, applying the disturbance rules."""

    @staticmethod
    def in_quiet_hours(prefs: NotificationPreferences, now: datetime | None = None) -> bool:
        if not prefs.respect_quiet_hours:
            return False
        now = now or datetime.now(UTC)
        current = now.hour
        start = prefs.quiet_hours_start
        end = prefs.quiet_hours_end
        if start == end:
            return False
        if start < end:
            return start <= current < end
        # Interval crosses midnight (e.g. 23 -> 7).
        return current >= start or current < end

    @staticmethod
    def can_interrupt(
        context: NotificationContext,
        category: str,
        prefs: NotificationPreferences,
    ) -> tuple[bool, str]:
        """Whether a live (in-ride) interruption is allowed right now."""
        if prefs.paused:
            return False, "notifications paused"
        if category == NotificationCategory.SAFETY.value:
            return True, "safety override"
        # Never interrupt Z4/Z5 unless it is a safety message.
        if context.intensity_zone is not None and context.intensity_zone >= 4:
            return False, "high intensity (Z4/Z5)"
        if SmartTiming.in_quiet_hours(prefs, context.now):
            # Non-urgent messages wait; safety already handled above.
            if category != NotificationCategory.SAFETY.value:
                return False, "quiet hours"
        return True, "ok"

    @staticmethod
    def min_voice_gap_seconds() -> int:
        # At least 5 minutes between voice messages during a ride.
        return 300


class MessageComposer:
    """Generates clear, coach-style messages in Italian (default) or English."""

    def __init__(self, language: str = "it"):
        self.language = language if language in ("it", "en") else "it"

    def compose(
        self,
        category: str,
        template_key: str,
        variables: dict[str, Any] | None = None,
        *,
        detailed: bool = False,
    ) -> tuple[str, str | None]:
        """Return (message, tts_text).

        ``tts_text`` is a shortened version (max 2 concepts) for the voice coach.
        """
        variables = variables or {}
        message = self._render(category, template_key, variables)
        if detailed:
            message = self._append_detail(category, template_key, variables, message)
        tts_text = self._shorten_for_voice(message)
        return message, tts_text

    def _render(self, category: str, key: str, vars: dict[str, Any]) -> str:
        lib = _MESSAGES[self.language][category]
        text = lib.get(key, lib.get("default", ""))
        try:
            return text.format(**vars)
        except (KeyError, IndexError, ValueError):
            return text

    def _append_detail(self, category: str, key: str, vars: dict[str, Any], base: str) -> str:
        detail = _DETAILS[self.language].get(category, {}).get(key)
        if not detail:
            return base
        try:
            detail = detail.format(**vars)
        except (KeyError, IndexError, ValueError):
            pass
        return f"{base}\n\n{detail}"

    @staticmethod
    def _shorten_for_voice(message: str) -> str:
        # Keep the first 1-2 sentences for spoken delivery.
        sentences = [s.strip() for s in message.replace("\n", " ").split(".") if s.strip()]
        if not sentences:
            return message
        if len(sentences) <= 2:
            return ". ".join(sentences) + "."
        return ". ".join(sentences[:2]) + "."


class NotificationRouter:
    """Selects the delivery channel and decides how/whether to send.

    Combines the evaluation score, smart-timing rules and athlete preferences
    to produce the final :class:`Notification` (or ``None`` when suppressed).
    """

    def __init__(self, prefs: NotificationPreferences | None = None):
        self.prefs = prefs or NotificationPreferences()

    def route(
        self,
        context: NotificationContext,
        category: str,
        template_key: str,
        variables: dict[str, Any] | None = None,
        *,
        notification_id: str | None = None,
        detailed: bool = False,
        signals: dict[str, Any] | None = None,
    ) -> Notification | None:
        score = ContextEvaluator.evaluate(context, category=category, signals=signals)
        if not score.should_notify:
            return None

        if self.prefs.paused:
            return None

        composer = MessageComposer(self.prefs.language)
        message, tts_text = composer.compose(
            category, template_key, variables, detailed=detailed
        )

        channel, priority = self._select_channel(context, category, score)
        if channel is None:
            return None

        return Notification(
            id=notification_id or self._new_id(),
            category=category,
            channel=channel.value if isinstance(channel, Channel) else channel,
            title=_TITLES[self.prefs.language].get(category, category),
            message=message,
            tts_text=tts_text if channel == Channel.VOICE.value else None,
            score=score.score,
            priority=priority,
            language=self.prefs.language,
            created_at=context.now,
        )

    def _select_channel(
        self, context: NotificationContext, category: str, score: NotificationScore
    ) -> tuple[Channel | None, int]:
        priority = _CATEGORY_PRIORITY.get(category, 5)

        # Safety (live) always tries voice first when allowed.
        if category == NotificationCategory.SAFETY.value:
            if self.prefs.allow_voice_coach and self.prefs.channel_priority:
                return Channel.VOICE, priority
            return Channel.APP, priority

        live = context.current_ride is not None

        if live:
            can, _why = SmartTiming.can_interrupt(context, category, self.prefs)
            if not can:
                # Defer to dashboard highlight (shown on app open) instead of
                # interrupting the athlete.
                return Channel.DASHBOARD, priority
            if self.prefs.allow_voice_coach and Channel.VOICE.value in self.prefs.channel_priority:
                return Channel.VOICE, priority
            return Channel.APP, priority

        # Background / not riding: follow athlete channel priority.
        for chan in self.prefs.channel_priority:
            c = Channel(chan)
            if c == Channel.VOICE and not self.prefs.allow_voice_coach:
                continue
            if c == Channel.EMAIL and not self.prefs.allow_email_summary:
                continue
            if c == Channel.VOICE:
                # Voice makes no sense without a live ride.
                continue
            return c, priority
        return Channel.APP, priority

    @staticmethod
    def batch(notifications: list[Notification], language: str = "it") -> Notification | None:
        """Group multiple notifications into a single batched message."""
        if not notifications:
            return None
        if len(notifications) == 1:
            return notifications[0]
        sorted_n = sorted(notifications, key=lambda n: n.priority)
        lines = [f"- {n.message}" for n in sorted_n]
        title = _TITLES.get(language, _TITLES["it"]).get("batch", "Aggiornamenti")
        body = "\n".join(lines)
        tts = MessageComposer._shorten_for_voice(body)
        return Notification(
            id="batch-" + sorted_n[0].id,
            category="batch",
            channel="app",
            title=title,
            message=body,
            tts_text=tts,
            score=round(sum(n.score for n in sorted_n) / len(sorted_n), 2),
            priority=sorted_n[0].priority,
            language=language,
            created_at=sorted_n[0].created_at,
        )

    @staticmethod
    def _new_id() -> str:
        return datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")


# ---------------------------------------------------------------------------
# Message templates (IT default, EN optional)
# ---------------------------------------------------------------------------

_MESSAGES: dict[str, dict[str, dict[str, str]]] = {
    "it": {
        "training": {
            "weather_changed": "Oggi avevi pianificato {plan}. Il meteo è cambiato: consideriamo un'alternativa.",
            "low_recovery_adjust": "Hai recuperato poco: modifichiamo il piano.",
            "default": "Promemoria di allenamento per oggi.",
        },
        "recovery": {
            "intense_yesterday": "Ieri è stato intenso: oggi serve scarico.",
            "good_recovery": "Hai 48 ore di recupero: ottimo per un'uscita lunga.",
            "default": "Priorità al recupero oggi.",
        },
        "performance": {
            "over_threshold": "La tua potenza media è del {pct}% sopra la soglia: stai spingendo troppo.",
            "goal_done": "Hai completato l'obiettivo settimanale: ecco il riepilogo.",
            "default": "Aggiornamento performance.",
        },
        "safety": {
            "traffic_ahead": "Traffico intenso tra {km} km: suggerisco una variante.",
            "stopped": "Hai fermato da {minutes} minuti: tutto ok?",
            "default": "Attenzione: verifica la tua situazione.",
        },
        "goal": {
            "granfondo_countdown": "Mancano {n} uscite per la granfondo: il carico è sulla soglia.",
            "ftp_improvement": "Hai migliorato il FTP del {pct}% questo mese.",
            "default": "Aggiornamento obiettivo.",
        },
    },
    "en": {
        "training": {
            "weather_changed": "You planned {plan} today. The weather changed: let's consider an alternative.",
            "low_recovery_adjust": "You recovered little: we adjust the plan.",
            "default": "Training reminder for today.",
        },
        "recovery": {
            "intense_yesterday": "Yesterday was intense: today you need an easy spin.",
            "good_recovery": "You have 48 hours of recovery: great for a long ride.",
            "default": "Prioritize recovery today.",
        },
        "performance": {
            "over_threshold": "Your average power is {pct}% above threshold: you are pushing too hard.",
            "goal_done": "You completed the weekly goal: here is the recap.",
            "default": "Performance update.",
        },
        "safety": {
            "traffic_ahead": "Heavy traffic in {km} km: I suggest an alternative route.",
            "stopped": "You stopped {minutes} minutes ago: are you ok?",
            "default": "Heads up: check your situation.",
        },
        "goal": {
            "granfondo_countdown": "{n} rides left to the granfondo: load is on the threshold.",
            "ftp_improvement": "You improved your FTP by {pct}% this month.",
            "default": "Goal update.",
        },
    },
}

_DETAILS: dict[str, dict[str, dict[str, str]]] = {
    "it": {
        "recovery": {
            "intense_yesterday": "TSB negativo: riduci intensità e privilegia zona 1-2.",
        },
        "performance": {
            "over_threshold": "Scendi di 5-10 W per rientrare nella soglia e proteggere la forma.",
        },
    },
    "en": {
        "recovery": {
            "intense_yesterday": "Negative TSB: lower intensity and favor zones 1-2.",
        },
        "performance": {
            "over_threshold": "Drop 5-10 W to return under threshold and protect your form.",
        },
    },
}

_TITLES: dict[str, dict[str, str]] = {
    "it": {
        "training": "Allenamento",
        "recovery": "Recupero",
        "performance": "Prestazione",
        "safety": "Sicurezza",
        "goal": "Obiettivi",
        "batch": "Aggiornamenti BikeMaster",
    },
    "en": {
        "training": "Training",
        "recovery": "Recovery",
        "performance": "Performance",
        "safety": "Safety",
        "goal": "Goals",
        "batch": "BikeMaster Updates",
    },
}


__all__ = [
    "Channel",
    "NotificationCategory",
    "NotificationContext",
    "NotificationScore",
    "Notification",
    "NotificationPreferences",
    "ContextEvaluator",
    "SmartTiming",
    "MessageComposer",
    "NotificationRouter",
    "MIN_NOTIFY_SCORE",
]
