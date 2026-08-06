"""Tests for proactive assistant module."""

from __future__ import annotations

from datetime import UTC, datetime

from bike_analyzer.backend.analytics.proactive import (
    ContextEvaluator,
    MessageComposer,
    NotificationCategory,
    NotificationContext,
    NotificationPreferences,
    SmartTiming,
)


class TestNotificationPreferences:
    def test_defaults(self):
        prefs = NotificationPreferences()
        assert prefs.language == "it"
        assert prefs.quiet_hours_start == 23
        assert prefs.quiet_hours_end == 7
        assert prefs.paused is False

    def test_from_dict_defaults(self):
        prefs = NotificationPreferences.from_dict({})
        assert prefs.language == "it"
        assert prefs.allow_voice_coach is True

    def test_from_dict_custom(self):
        prefs = NotificationPreferences.from_dict({
            "language": "en",
            "quiet_hours_start": 22,
            "quiet_hours_end": 6,
            "paused": True,
            "channel_priority": ["voice", "app"],
        })
        assert prefs.language == "en"
        assert prefs.quiet_hours_start == 22
        assert prefs.quiet_hours_end == 6
        assert prefs.paused is True
        assert prefs.channel_priority == ["voice", "app"]

    def test_from_dict_filters_invalid_channels(self):
        prefs = NotificationPreferences.from_dict({
            "channel_priority": ["invalid", "app", "telegram"],
        })
        assert prefs.channel_priority == ["app"]


class TestSmartTiming:
    def test_in_quiet_hours_inside_window(self):
        prefs = NotificationPreferences(quiet_hours_start=23, quiet_hours_end=7, respect_quiet_hours=True)
        now = datetime(2024, 6, 15, 2, 0, tzinfo=UTC)
        assert SmartTiming.in_quiet_hours(prefs, now) is True

    def test_in_quiet_hours_outside_window(self):
        prefs = NotificationPreferences(quiet_hours_start=23, quiet_hours_end=7, respect_quiet_hours=True)
        now = datetime(2024, 6, 15, 14, 0, tzinfo=UTC)
        assert SmartTiming.in_quiet_hours(prefs, now) is False

    def test_in_quiet_hours_disabled(self):
        prefs = NotificationPreferences(respect_quiet_hours=False)
        now = datetime(2024, 6, 15, 2, 0, tzinfo=UTC)
        assert SmartTiming.in_quiet_hours(prefs, now) is False

    def test_in_quiet_hours_cross_midnight(self):
        prefs = NotificationPreferences(quiet_hours_start=22, quiet_hours_end=6, respect_quiet_hours=True)
        assert SmartTiming.in_quiet_hours(prefs, datetime(2024, 6, 15, 23, 30, tzinfo=UTC)) is True
        assert SmartTiming.in_quiet_hours(prefs, datetime(2024, 6, 15, 3, 0, tzinfo=UTC)) is True
        assert SmartTiming.in_quiet_hours(prefs, datetime(2024, 6, 15, 10, 0, tzinfo=UTC)) is False

    def test_in_quiet_hours_same_start_end(self):
        prefs = NotificationPreferences(quiet_hours_start=7, quiet_hours_end=7, respect_quiet_hours=True)
        now = datetime(2024, 6, 15, 7, 0, tzinfo=UTC)
        assert SmartTiming.in_quiet_hours(prefs, now) is False

    def test_can_interrupt_safety_always(self):
        prefs = NotificationPreferences()
        ctx = NotificationContext(intensity_zone=5)
        can, reason = SmartTiming.can_interrupt(ctx, NotificationCategory.SAFETY.value, prefs)
        assert can is True
        assert reason == "safety override"

    def test_can_interrupt_paused(self):
        prefs = NotificationPreferences(paused=True)
        ctx = NotificationContext()
        can, reason = SmartTiming.can_interrupt(ctx, NotificationCategory.TRAINING.value, prefs)
        assert can is False
        assert reason == "notifications paused"

    def test_can_interrupt_high_intensity(self):
        prefs = NotificationPreferences()
        ctx = NotificationContext(intensity_zone=4)
        can, reason = SmartTiming.can_interrupt(ctx, NotificationCategory.TRAINING.value, prefs)
        assert can is False
        assert reason == "high intensity (Z4/Z5)"

    def test_can_interrupt_quiet_hours(self):
        prefs = NotificationPreferences(quiet_hours_start=0, quiet_hours_end=5, respect_quiet_hours=True)
        ctx = NotificationContext(now=datetime(2024, 6, 15, 1, 0, tzinfo=UTC))
        can, reason = SmartTiming.can_interrupt(ctx, NotificationCategory.TRAINING.value, prefs)
        assert can is False
        assert reason == "quiet hours"

    def test_can_interrupt_ok(self):
        prefs = NotificationPreferences()
        ctx = NotificationContext(intensity_zone=2, now=datetime(2024, 6, 15, 14, 0, tzinfo=UTC))
        can, reason = SmartTiming.can_interrupt(ctx, NotificationCategory.TRAINING.value, prefs)
        assert can is True
        assert reason == "ok"

    def test_min_voice_gap(self):
        assert SmartTiming.min_voice_gap_seconds() == 300


class TestContextEvaluator:
    def test_safety_always_notifies(self):
        ctx = NotificationContext()
        score = ContextEvaluator.evaluate(ctx, category=NotificationCategory.SAFETY.value)
        assert score.should_notify is True

    def test_low_score_no_notify(self):
        ctx = NotificationContext()
        score = ContextEvaluator.evaluate(ctx, category=NotificationCategory.GOAL.value)
        assert score.should_notify is False

    def test_risk_boosts_urgency(self):
        ctx = NotificationContext()
        score = ContextEvaluator.evaluate(ctx, category=NotificationCategory.TRAINING.value, signals={"risk": True})
        assert score.urgency == 5
        assert "risk detected" in score.reasons

    def test_recovery_insufficient_recovery_boosts(self):
        ctx = NotificationContext(athlete_state={"tsb": -20})
        score = ContextEvaluator.evaluate(ctx, category=NotificationCategory.RECOVERY.value, signals={"insufficient_recovery": True})
        assert score.urgency >= 4
        assert "insufficient recovery" in score.reasons

    def test_goal_linked_to_active_plan(self):
        ctx = NotificationContext(plan={"goal_active": True})
        score = ContextEvaluator.evaluate(ctx, category=NotificationCategory.GOAL.value)
        assert score.relevance == 5
        assert "linked to active goal" in score.reasons

    def test_training_matches_today(self):
        ctx = NotificationContext(plan={"planned_today": True})
        score = ContextEvaluator.evaluate(ctx, category=NotificationCategory.TRAINING.value)
        assert score.relevance == 4
        assert "matches today's plan" in score.reasons

    def test_already_known_lowers_relevance(self):
        ctx = NotificationContext()
        score = ContextEvaluator.evaluate(ctx, category=NotificationCategory.TRAINING.value, signals={"already_known": True})
        assert score.relevance == 1

    def test_stale_lowers_timeliness(self):
        ctx = NotificationContext()
        score = ContextEvaluator.evaluate(ctx, category=NotificationCategory.TRAINING.value, signals={"stale": True})
        assert score.timeliness == 1

    def test_scores_bounded_1_to_5(self):
        ctx = NotificationContext()
        score = ContextEvaluator.evaluate(ctx, category=NotificationCategory.SAFETY.value, signals={"risk": True, "insufficient_recovery": True})
        for dim in (score.urgency, score.relevance, score.timeliness):
            assert 1 <= dim <= 5

    def test_score_is_mean_of_three(self):
        ctx = NotificationContext()
        score = ContextEvaluator.evaluate(ctx, category=NotificationCategory.SAFETY.value)
        expected = round((score.urgency + score.relevance + score.timeliness) / 3.0, 2)
        assert score.score == expected


class TestMessageComposer:
    def test_default_language_italian(self):
        mc = MessageComposer()
        assert mc.language == "it"

    def test_english_language(self):
        mc = MessageComposer(language="en")
        assert mc.language == "en"

    def test_invalid_language_fallback(self):
        mc = MessageComposer(language="fr")
        assert mc.language == "it"

    def test_compose_returns_tuple(self):
        mc = MessageComposer()
        result = mc.compose("training", "test_key")
        assert isinstance(result, tuple)
        assert len(result) == 2
