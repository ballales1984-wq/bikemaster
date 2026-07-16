"""Tests for the training plan engine system."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bike_analyzer.backend.analytics.training import (
    AdaptationEngine,
    AdaptationEvent,
    AdaptationEventType,
    AdaptationRules,
    ConstraintSolver,
    GoalAnalyzer,
    GoalType,
    PlanConstraints,
    ScenarioGenerator,
    ScenarioType,
    TrainingGoal,
    WeeklyPlan,
    Workout,
    WorkoutGenerator,
    WorkoutType,
    PlanDistributor,
)
from bike_analyzer.backend.models.models import AthleteProfile, Ride


class TestTrainingGoal:
    def test_granfondo_goal(self):
        g = TrainingGoal(goal_type=GoalType.GRANFONDO, target_date="2025-12-01", target_distance_km=100.0)
        assert g.goal_type == GoalType.GRANFONDO
        assert g.target_distance_km == 100.0

    def test_invalid_date_raises(self):
        with pytest.raises(Exception):
            TrainingGoal(goal_type=GoalType.GRANFONDO, target_date="not-a-date")

    def test_defaults(self):
        g = TrainingGoal()
        assert g.goal_type == GoalType.MAINTENANCE
        assert g.target_date is None


class TestPlanConstraints:
    def test_defaults(self):
        c = PlanConstraints()
        assert c.days_per_week == 3
        assert c.hours_per_session == 1.5

    def test_invalid_windows_filtered(self):
        c = PlanConstraints(preferred_windows=["morning", "invalid"])
        assert "invalid" not in c.preferred_windows
        assert "morning" in c.preferred_windows

    def test_equipment_from_profile(self):
        athlete = AthleteProfile(equipment="road_bike, smart_trainer")
        solver = ConstraintSolver(athlete)
        c = solver.solve()
        assert "road_bike" in c.equipment
        assert "smart_trainer" in c.equipment


class TestGoalAnalyzer:
    def test_explicit_goal(self):
        athlete = AthleteProfile(name="Mario", experience_level="Intermediate")
        analyzer = GoalAnalyzer(athlete)
        goal = TrainingGoal(goal_type=GoalType.FTP_IMPROVEMENT)
        result = analyzer.analyze(goal)
        assert result.goal_type == GoalType.FTP_IMPROVEMENT

    def test_free_text_granfondo(self):
        athlete = AthleteProfile(name="Mario", experience_level="Intermediate")
        analyzer = GoalAnalyzer(athlete)
        result = analyzer.analyze("Voglio preparare una granfondo a settembre")
        assert result.goal_type == GoalType.GRANFONDO

    def test_free_text_ftp(self):
        athlete = AthleteProfile(name="Mario", experience_level="Intermediate")
        analyzer = GoalAnalyzer(athlete)
        result = analyzer.analyze("Aumentare il FTP di 10W")
        assert result.goal_type == GoalType.FTP_IMPROVEMENT

    def test_free_text_weight_loss(self):
        athlete = AthleteProfile(name="Mario", experience_level="Intermediate")
        analyzer = GoalAnalyzer(athlete)
        result = analyzer.analyze("Perdere peso")
        assert result.goal_type == GoalType.WEIGHT_LOSS

    def test_free_text_beginner(self):
        athlete = AthleteProfile(name="Mario", experience_level="Beginner")
        analyzer = GoalAnalyzer(athlete)
        result = analyzer.analyze("Sono un principiante")
        assert result.goal_type == GoalType.BEGINNER_BASE

    def test_empty_fallback(self):
        athlete = AthleteProfile(name="Mario", experience_level="Beginner")
        analyzer = GoalAnalyzer(athlete)
        result = analyzer.analyze(None)
        assert result.goal_type == GoalType.BEGINNER_BASE

    def test_target_weekly_tss_beginner(self):
        athlete = AthleteProfile(name="Mario", experience_level="Beginner")
        analyzer = GoalAnalyzer(athlete)
        goal = TrainingGoal(goal_type=GoalType.MAINTENANCE)
        assert analyzer.target_weekly_tss(goal) == 150.0

    def test_target_weekly_tss_advanced(self):
        athlete = AthleteProfile(name="Mario", experience_level="Advanced")
        analyzer = GoalAnalyzer(athlete)
        goal = TrainingGoal(goal_type=GoalType.GRANFONDO)
        assert analyzer.target_weekly_tss(goal) == 500.0 * 1.3

    def test_plan_duration_from_date(self):
        athlete = AthleteProfile(name="Mario", experience_level="Intermediate")
        analyzer = GoalAnalyzer(athlete)
        goal = TrainingGoal(goal_type=GoalType.GRANFONDO, target_date="2025-12-01")
        weeks = analyzer.plan_duration_weeks(goal)
        assert weeks > 0


class TestConstraintSolver:
    def test_solve_defaults(self):
        athlete = AthleteProfile(name="Mario", experience_level="Beginner")
        solver = ConstraintSolver(athlete)
        c = solver.solve()
        assert c.days_per_week >= 1

    def test_validate_valid(self):
        c = PlanConstraints(days_per_week=3, hours_per_session=1.5)
        solver = ConstraintSolver(AthleteProfile())
        warnings = solver.validate(c)
        assert warnings == []

    def test_validate_zero_days_caught_by_pydantic(self):
        with pytest.raises(Exception):
            PlanConstraints(days_per_week=0)

    def test_validate_too_many_days(self):
        c = PlanConstraints(days_per_week=10)
        solver = ConstraintSolver(AthleteProfile())
        warnings = solver.validate(c)
        assert any("exceeds 7" in w for w in warnings)

    def test_overrides_applied(self):
        athlete = AthleteProfile(name="Mario", experience_level="Beginner")
        solver = ConstraintSolver(athlete)
        c = solver.solve(PlanConstraints(days_per_week=5))
        assert c.days_per_week == 5


class TestWorkoutGenerator:
    def test_generates_correct_count(self):
        athlete = AthleteProfile(name="Mario", experience_level="Beginner", ftp_watts=200.0)
        gen = WorkoutGenerator(athlete)
        goal = TrainingGoal(goal_type=GoalType.MAINTENANCE)
        constraints = PlanConstraints(days_per_week=3)
        start = datetime(2024, 6, 1, tzinfo=UTC)
        workouts = gen.generate_for_week(goal, constraints, start)
        assert len(workouts) == 3

    def test_workout_has_blocks(self):
        athlete = AthleteProfile(name="Mario", experience_level="Beginner", ftp_watts=200.0)
        gen = WorkoutGenerator(athlete)
        goal = TrainingGoal(goal_type=GoalType.MAINTENANCE)
        constraints = PlanConstraints(days_per_week=2)
        start = datetime(2024, 6, 1, tzinfo=UTC)
        workouts = gen.generate_for_week(goal, constraints, start)
        for w in workouts:
            assert len(w.blocks) >= 1
            assert any(b.block_type == "warmup" for b in w.blocks)
            assert any(b.block_type == "cooldown" for b in w.blocks)

    def test_fatigue_reduces_duration(self):
        athlete = AthleteProfile(name="Mario", experience_level="Intermediate", ftp_watts=250.0)
        gen = WorkoutGenerator(athlete)
        goal = TrainingGoal(goal_type=GoalType.MAINTENANCE)
        constraints = PlanConstraints(days_per_week=3, hours_per_session=2.0)
        start = datetime(2024, 6, 1, tzinfo=UTC)
        low = gen.generate_for_week(goal, constraints, start, fatigue_score=2.0)
        high = gen.generate_for_week(goal, constraints, start, fatigue_score=8.0)
        avg_low = sum(w.duration_minutes for w in low) / len(low)
        avg_high = sum(w.duration_minutes for w in high) / len(high)
        assert avg_low > avg_high

    def test_intervals_have_reps(self):
        athlete = AthleteProfile(name="Mario", experience_level="Advanced", ftp_watts=300.0)
        gen = WorkoutGenerator(athlete)
        goal = TrainingGoal(goal_type=GoalType.FTP_IMPROVEMENT)
        constraints = PlanConstraints(days_per_week=4)
        start = datetime(2024, 6, 1, tzinfo=UTC)
        workouts = gen.generate_for_week(goal, constraints, start)
        intervals = [w for w in workouts if w.workout_type == WorkoutType.INTERVALS]
        assert len(intervals) >= 1
        for w in intervals:
            main_blocks = [b for b in w.blocks if b.block_type == "main"]
            assert len(main_blocks) >= 1
            assert main_blocks[0].repetition_count >= 1


class TestPlanDistributor:
    def test_distributes_correct_weeks(self):
        athlete = AthleteProfile(name="Mario", experience_level="Intermediate", ftp_watts=250.0)
        dist = PlanDistributor(athlete)
        gen = WorkoutGenerator(athlete)
        goal = TrainingGoal(goal_type=GoalType.MAINTENANCE)
        constraints = PlanConstraints(days_per_week=3)
        start = datetime(2024, 6, 1, tzinfo=UTC)
        plan = dist.distribute(goal, constraints, start, gen)
        assert plan.phase in ("base", "build", "peak")
        assert plan.total_tss > 0
        assert plan.microcycle_weeks >= 1

    def test_recovery_week_included(self):
        athlete = AthleteProfile(name="Mario", experience_level="Advanced", ftp_watts=300.0)
        dist = PlanDistributor(athlete)
        gen = WorkoutGenerator(athlete)
        goal = TrainingGoal(goal_type=GoalType.GRANFONDO, target_date="2027-09-01")
        constraints = PlanConstraints(days_per_week=4)
        start = datetime(2027, 6, 1, tzinfo=UTC)
        plan = dist.distribute(goal, constraints, start, gen)
        assert plan.microcycle_weeks >= 3
        total_workouts = len(plan.days)
        assert total_workouts >= 4 * 3

    def test_granfondo_tapering(self):
        athlete = AthleteProfile(name="Mario", experience_level="Advanced", ftp_watts=300.0)
        dist = PlanDistributor(athlete)
        gen = WorkoutGenerator(athlete)
        goal = TrainingGoal(goal_type=GoalType.GRANFONDO, target_date="2027-12-01")
        constraints = PlanConstraints(days_per_week=4)
        start = datetime(2027, 6, 1, tzinfo=UTC)
        plan = dist.distribute(goal, constraints, start, gen)
        assert plan.end_date >= "2027-11-01"


class TestAdaptationRules:
    def test_skipped_increases_remaining(self):
        athlete = AthleteProfile(name="Mario", experience_level="Intermediate", ftp_watts=250.0)
        gen = WorkoutGenerator(athlete)
        goal = TrainingGoal(goal_type=GoalType.MAINTENANCE)
        constraints = PlanConstraints(days_per_week=3)
        start = datetime(2024, 6, 1, tzinfo=UTC)
        workouts = gen.generate_for_week(goal, constraints, start)
        plan = WeeklyPlan(start_date=start.strftime("%Y-%m-%d"), end_date=(start).strftime("%Y-%m-%d"), days=workouts, total_tss=sum(w.estimated_tss for w in workouts), microcycle_weeks=1)

        missed = workouts[0]
        event = AdaptationEvent(event_type=AdaptationEventType.SKIPPED, occurred_date=missed.date, planned_workout=missed)
        adapted = AdaptationRules.apply(event, plan)
        assert sum(d.estimated_tss for d in adapted.days) >= plan.total_tss - missed.estimated_tss

    def test_injury_sets_recovery(self):
        athlete = AthleteProfile(name="Mario", experience_level="Intermediate", ftp_watts=250.0)
        gen = WorkoutGenerator(athlete)
        goal = TrainingGoal(goal_type=GoalType.MAINTENANCE)
        constraints = PlanConstraints(days_per_week=3)
        start = datetime(2024, 6, 1, tzinfo=UTC)
        workouts = gen.generate_for_week(goal, constraints, start)
        plan = WeeklyPlan(start_date=start.strftime("%Y-%m-%d"), end_date=(start).strftime("%Y-%m-%d"), days=workouts, total_tss=sum(w.estimated_tss for w in workouts), microcycle_weeks=1)

        event = AdaptationEvent(event_type=AdaptationEventType.INJURY, occurred_date=start.strftime("%Y-%m-%d"))
        adapted = AdaptationRules.apply(event, plan)
        for d in adapted.days:
            assert d.workout_type == WorkoutType.RECOVERY
            assert d.duration_minutes <= 30


class TestAdaptationEngine:
    def test_should_notify_injury(self):
        athlete = AthleteProfile(name="Mario", experience_level="Intermediate")
        engine = AdaptationEngine(athlete)
        plan = WeeklyPlan(start_date="2024-06-01", end_date="2024-06-07", days=[])
        event = AdaptationEvent(event_type=AdaptationEventType.INJURY, occurred_date="2024-06-01")
        should, msg = engine.should_notify(plan, event)
        assert should is True
        assert len(msg) > 0

    def test_no_notify_skip(self):
        athlete = AthleteProfile(name="Mario", experience_level="Intermediate")
        engine = AdaptationEngine(athlete)
        plan = WeeklyPlan(start_date="2024-06-01", end_date="2024-06-07", days=[])
        event = AdaptationEvent(event_type=AdaptationEventType.SKIPPED, occurred_date="2024-06-01")
        should, _ = engine.should_notify(plan, event)
        assert should is False


class TestScenarioGenerator:
    def test_generates_three_scenarios(self):
        athlete = AthleteProfile(name="Mario", experience_level="Intermediate", ftp_watts=250.0)
        gen = ScenarioGenerator(athlete)
        goal = TrainingGoal(goal_type=GoalType.MAINTENANCE)
        constraints = PlanConstraints(days_per_week=3)
        start = datetime(2024, 6, 1, tzinfo=UTC)
        base_workouts = WorkoutGenerator(athlete).generate_for_week(goal, constraints, start)
        base = WeeklyPlan(start_date=start.strftime("%Y-%m-%d"), end_date=(start).strftime("%Y-%m-%d"), days=base_workouts, total_tss=sum(w.estimated_tss for w in base_workouts), microcycle_weeks=1)
        scenarios = gen.generate_scenarios(goal, constraints, base)
        assert len(scenarios) == 3
        types = {s.scenario_type for s in scenarios}
        assert ScenarioType.RECOVER_VOLUME in types
        assert ScenarioType.MAINTAIN_PLAN in types
        assert ScenarioType.CHANGE_TYPE in types

    def test_scenarios_scored(self):
        athlete = AthleteProfile(name="Mario", experience_level="Intermediate", ftp_watts=250.0)
        gen = ScenarioGenerator(athlete)
        goal = TrainingGoal(goal_type=GoalType.MAINTENANCE)
        constraints = PlanConstraints(days_per_week=3)
        start = datetime(2024, 6, 1, tzinfo=UTC)
        base_workouts = WorkoutGenerator(athlete).generate_for_week(goal, constraints, start)
        base = WeeklyPlan(start_date=start.strftime("%Y-%m-%d"), end_date=(start).strftime("%Y-%m-%d"), days=base_workouts, total_tss=sum(w.estimated_tss for w in base_workouts), microcycle_weeks=1)
        scenarios = gen.generate_scenarios(goal, constraints, base)
        for s in scenarios:
            assert s.score >= 0.0
            assert len(s.label) > 0
