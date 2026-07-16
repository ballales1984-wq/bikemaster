"""Unit tests for the GoalAnalyzer training-goal interpreter."""

from dataclasses import dataclass

import pytest

from bike_analyzer.backend.analytics.training.goal_analyzer import GoalAnalyzer
from bike_analyzer.backend.analytics.training.models import GoalType, TrainingGoal


@dataclass
class _Athlete:
    experience_level: str = "Beginner"
    goals: str = ""


def test_analyze_explicit_training_goal():
    a = GoalAnalyzer(_Athlete(experience_level="Advanced"))
    goal = TrainingGoal(goal_type=GoalType.GRANFONDO, description="GF")
    assert a.analyze(goal) is goal


def test_analyze_free_text_granfondo():
    a = GoalAnalyzer(_Athlete())
    goal = a.analyze("Voglio preparare una granfondo di 120km")
    assert goal.goal_type == GoalType.GRANFONDO


def test_analyze_free_text_ftp():
    a = GoalAnalyzer(_Athlete())
    goal = a.analyze("Migliorare la soglia FTP")
    assert goal.goal_type == GoalType.FTP_IMPROVEMENT


def test_analyze_free_text_weight_loss():
    a = GoalAnalyzer(_Athlete())
    goal = a.analyze("Perdere peso e grasso")
    assert goal.goal_type == GoalType.WEIGHT_LOSS


def test_analyze_free_text_beginner():
    a = GoalAnalyzer(_Athlete())
    goal = a.analyze("Sono un principiante, voglio iniziare")
    assert goal.goal_type == GoalType.BEGINNER_BASE


def test_analyze_fallback_beginner():
    a = GoalAnalyzer(_Athlete(experience_level="Beginner"))
    goal = a.analyze(None)
    assert goal.goal_type == GoalType.BEGINNER_BASE


def test_analyze_fallback_maintenance_for_advanced():
    a = GoalAnalyzer(_Athlete(experience_level="Advanced"))
    goal = a.analyze("")
    assert goal.goal_type == GoalType.MAINTENANCE


def test_target_weekly_tss_by_level_and_type():
    a = GoalAnalyzer(_Athlete(experience_level="Beginner"))
    gf = TrainingGoal(goal_type=GoalType.GRANFONDO)
    ftp = TrainingGoal(goal_type=GoalType.FTP_IMPROVEMENT)
    assert a.target_weekly_tss(gf) == pytest.approx(150.0 * 1.3)
    assert a.target_weekly_tss(ftp) == pytest.approx(150.0 * 1.4)
    assert a.target_weekly_tss(TrainingGoal(goal_type=GoalType.WEIGHT_LOSS)) == pytest.approx(150.0 * 0.9)


def test_plan_duration_weeks_fallback():
    a = GoalAnalyzer(_Athlete())
    assert a.plan_duration_weeks(TrainingGoal(goal_type=GoalType.MAINTENANCE)) == 8
    ftp = TrainingGoal(goal_type=GoalType.FTP_IMPROVEMENT, ftp_timeframe_weeks=12)
    assert a.plan_duration_weeks(ftp) == 12


def test_plan_duration_weeks_target_date():
    a = GoalAnalyzer(_Athlete())
    from datetime import date, timedelta

    future = (date.today() + timedelta(weeks=10)).isoformat()
    goal = TrainingGoal(goal_type=GoalType.GRANFONDO, target_date=future)
    assert a.plan_duration_weeks(goal) == 10


def test_taper_weeks_event():
    a = GoalAnalyzer(_Athlete())
    from datetime import date, timedelta

    future = (date.today() + timedelta(weeks=12)).isoformat()
    goal = TrainingGoal(goal_type=GoalType.GRANFONDO, target_date=future)
    assert a.taper_weeks(goal) >= 1
