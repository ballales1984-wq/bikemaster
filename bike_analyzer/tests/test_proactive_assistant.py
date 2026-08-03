"""Tests for the Proactive Assistant notification engine.

Covers the required scenarios: context evaluation (score/threshold), smart
timing (quiet hours, Z4/Z5 interruption, gaps), channel routing, message
composer (IT/EN, voice shortening) and notification batching.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bike_analyzer.backend.analytics.proactive import (
    MIN_NOTIFY_SCORE,
    Channel,
    ContextEvaluator,
    MessageComposer,
    NotificationCategory,
    NotificationContext,
    NotificationPreferences,
    NotificationRouter,
    SmartTiming,
)
from bike_analyzer.backend.analytics.voice_coach import (
    VoiceCoach,
    VoiceCommand,
    VoiceCommandParser,
)


def _ctx(intensity_zone=None, tsb=0, plan=None) -> NotificationContext:
    return NotificationContext(
        athlete_state={"tsb": tsb},
        plan=plan,
        intensity_zone=intensity_zone,
        now=datetime(2026, 7, 16, 10, 0, tzinfo=UTC),
    )


# --- Context Evaluator ------------------------------------------------------
def test_score_below_threshold_is_suppressed():
    ctx = _ctx(tsb=10)
    score = ContextEvaluator.evaluate(ctx, category=NotificationCategory.GOAL.value, signals={"minor_stat": True})
    assert score.score < MIN_NOTIFY_SCORE
    assert score.should_notify is False


def test_safety_always_notifies_despite_low_score():
    ctx = _ctx(tsb=10)
    score = ContextEvaluator.evaluate(ctx, category=NotificationCategory.SAFETY.value, signals={})
    assert score.score >= MIN_NOTIFY_SCORE
    assert score.should_notify is True


def test_recovery_with_low_tsb_scores_high():
    ctx = _ctx(tsb=-25)
    score = ContextEvaluator.evaluate(
        ctx, category=NotificationCategory.RECOVERY.value, signals={"insufficient_recovery": True}
    )
    assert score.urgency >= 4
    assert score.relevance >= 4
    assert score.should_notify is True


def test_score_formula_is_mean_of_three():
    ctx = _ctx()
    score = ContextEvaluator.evaluate(ctx, category=NotificationCategory.TRAINING.value, signals={})
    assert score.score == pytest.approx((score.urgency + score.relevance + score.timeliness) / 3.0)


# --- Smart Timing -----------------------------------------------------------
def test_quiet_hours_blocks_non_safety():
    prefs = NotificationPreferences(quiet_hours_start=23, quiet_hours_end=7)
    now = datetime(2026, 7, 16, 2, 0, tzinfo=UTC)
    ctx = NotificationContext(now=now)
    can, why = SmartTiming.can_interrupt(ctx, NotificationCategory.TRAINING.value, prefs)
    assert can is False
    assert why == "quiet hours"


def test_quiet_hours_does_not_block_safety():
    prefs = NotificationPreferences(quiet_hours_start=23, quiet_hours_end=7)
    now = datetime(2026, 7, 16, 2, 0, tzinfo=UTC)
    ctx = NotificationContext(now=now)
    can, _ = SmartTiming.can_interrupt(ctx, NotificationCategory.SAFETY.value, prefs)
    assert can is True


def test_no_interrupt_during_z4_z5():
    prefs = NotificationPreferences()
    ctx = _ctx(intensity_zone=4)
    can, why = SmartTiming.can_interrupt(ctx, NotificationCategory.PERFORMANCE.value, prefs)
    assert can is False
    assert "Z4/Z5" in why


def test_z3_allows_interrupt():
    prefs = NotificationPreferences()
    ctx = _ctx(intensity_zone=2)
    can, _ = SmartTiming.can_interrupt(ctx, NotificationCategory.PERFORMANCE.value, prefs)
    assert can is True


def test_paused_blocks_everything():
    prefs = NotificationPreferences(paused=True)
    ctx = _ctx()
    can, _ = SmartTiming.can_interrupt(ctx, NotificationCategory.SAFETY.value, prefs)
    assert can is False


# --- Message Composer -------------------------------------------------------
def test_compose_italian_template():
    composer = MessageComposer("it")
    msg, tts = composer.compose(NotificationCategory.PERFORMANCE.value, "over_threshold", {"pct": 5})
    assert "5%" in msg
    assert "sopra la soglia" in msg
    assert tts is not None


def test_compose_english_template():
    composer = MessageComposer("en")
    msg, tts = composer.compose(NotificationCategory.SAFETY.value, "stopped", {"minutes": 10})
    assert "10 minutes" in msg


def test_voice_shortening_keeps_two_sentences():
    composer = MessageComposer("it")
    long_text = "Frase uno. Frase due. Frase tre che non serve. Frase quattro inutile."
    tts = composer._shorten_for_voice(long_text)
    assert tts.count(".") <= 2
    assert "Frase uno" in tts
    assert "Frase tre" not in tts


def test_detailed_appends_detail():
    composer = MessageComposer("it")
    msg, _ = composer.compose(NotificationCategory.PERFORMANCE.value, "over_threshold", {"pct": 5}, detailed=True)
    assert "Scendi di" in msg


# --- Notification Router ----------------------------------------------------
def test_router_returns_none_below_threshold():
    router = NotificationRouter(NotificationPreferences())
    n = router.route(_ctx(tsb=10), NotificationCategory.GOAL.value, "default", {}, signals={"minor_stat": True})
    assert n is None


def test_router_picks_voice_for_safety_live():
    prefs = NotificationPreferences(allow_voice_coach=True)
    router = NotificationRouter(prefs)
    ctx = _ctx(intensity_zone=2)
    ctx.current_ride = {"id": 1}
    n = router.route(ctx, NotificationCategory.SAFETY.value, "stopped", {"minutes": 10})
    assert n is not None
    assert n.channel == Channel.VOICE.value
    assert n.tts_text is not None


def test_router_defers_to_dashboard_during_high_intensity():
    prefs = NotificationPreferences()
    router = NotificationRouter(prefs)
    ctx = _ctx(intensity_zone=4)
    ctx.current_ride = {"id": 1}
    n = router.route(
        ctx, NotificationCategory.RECOVERY.value, "intense_yesterday", {}, signals={"insufficient_recovery": True}
    )
    assert n is not None
    assert n.channel == Channel.DASHBOARD.value


def test_router_background_uses_channel_priority():
    prefs = NotificationPreferences(channel_priority=["email", "app"])
    router = NotificationRouter(prefs)
    n = router.route(
        _ctx(tsb=-25),
        NotificationCategory.RECOVERY.value,
        "intense_yesterday",
        {},
        signals={"insufficient_recovery": True},
    )
    assert n is not None
    assert n.channel == Channel.EMAIL.value


def test_batch_groups_multiple_notifications():
    prefs = NotificationPreferences()
    router = NotificationRouter(prefs)
    ns = [
        router.route(
            _ctx(tsb=-25),
            NotificationCategory.RECOVERY.value,
            "intense_yesterday",
            {},
            signals={"insufficient_recovery": True},
        ),
        router.route(
            _ctx(tsb=5, plan={"goal_active": True}),
            NotificationCategory.GOAL.value,
            "granfondo_countdown",
            {"n": 3},
            signals={},
        ),
    ]
    ns = [x for x in ns if x]
    batched = NotificationRouter.batch(ns, "it")
    assert batched is not None
    assert batched.category == "batch"
    assert "- " in batched.message


# --- Voice Coach ------------------------------------------------------------
def test_voice_command_parser_italian():
    p = VoiceCommandParser.parse("Come sto andando?")
    assert p.command == VoiceCommand.STATUS


def test_voice_command_parser_stop():
    p = VoiceCommandParser.parse("Stop")
    assert p.command == VoiceCommand.STOP


def test_voice_command_parser_unknown():
    p = VoiceCommandParser.parse("ciao bel tempo")
    assert p.command == VoiceCommand.UNKNOWN


def test_voice_coach_blocks_z4_z5():
    coach = VoiceCoach("it")
    spoken = coach.speak_message(NotificationCategory.PERFORMANCE.value, "over_threshold", {"pct": 5}, intensity_zone=4)
    assert spoken is None


def test_voice_coach_enforces_gap():
    coach = VoiceCoach("it", last_spoken_at=1000.0)
    # too soon (< 300s gap)
    spoken = coach.speak_message(
        NotificationCategory.RECOVERY.value, "intense_yesterday", {}, intensity_zone=2, now_ts=1100.0
    )
    assert spoken is None
    # gap elapsed
    spoken2 = coach.speak_message(
        NotificationCategory.RECOVERY.value, "intense_yesterday", {}, intensity_zone=2, now_ts=1500.0
    )
    assert spoken2 is not None


def test_voice_cue():
    coach = VoiceCoach("it")
    cue = coach.cue("warmup")
    assert cue == "Inizia riscaldamento"
