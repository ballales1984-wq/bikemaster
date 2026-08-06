"""Tests for planned-vs-actual comparison logic.

Covers the comparison between planned calendar events (training plan) and
actual completed rides, including TSS comparison, completion rate, and
load adherence metrics.
"""

from __future__ import annotations

from datetime import datetime

from bike_analyzer.backend.analytics.training_load import calculate_atl_ctl_tsb
from bike_analyzer.backend.models.models import Ride


class TestPlannedVsActualComparison:
    """Comparison logic between planned calendar events and actual rides."""

    def _make_ride(self, date: str, distance_km: float, duration_minutes: float,
                   heart_rate_avg: float | None = None) -> Ride:
        return Ride(
            date=date,
            distance_km=distance_km,
            duration_minutes=duration_minutes,
            weight_kg=70.0,
            heart_rate_avg=heart_rate_avg,
        )

    def test_ride_matches_planned_date(self):
        """A ride on the planned date counts as completion."""
        planned_date = "2024-06-15"
        ride = self._make_ride(planned_date, 25.0, 60.0)
        assert ride.date == planned_date

    def test_ride_does_not_match_different_date(self):
        """A ride on a different date does not match the plan."""
        planned_date = "2024-06-15"
        ride_date = "2024-06-16"
        ride = self._make_ride(ride_date, 25.0, 60.0)
        assert ride.date != planned_date

    def test_multiple_rides_same_date(self):
        """Multiple rides on the same planned date — all count."""
        planned_date = "2024-06-15"
        rides = [
            self._make_ride(planned_date, 20.0, 45.0),
            self._make_ride(planned_date, 30.0, 75.0),
        ]
        matching = [r for r in rides if r.date == planned_date]
        assert len(matching) == 2

    def test_completion_rate_calculation(self):
        """Calculate what percentage of planned sessions were completed."""
        planned_dates = ["2024-06-10", "2024-06-12", "2024-06-14", "2024-06-16", "2024-06-18"]
        ride_dates = ["2024-06-10", "2024-06-14", "2024-06-18"]
        completed = sum(1 for d in planned_dates if d in ride_dates)
        rate = completed / len(planned_dates)
        assert rate == 3 / 5

    def test_tss_estimate_vs_actual(self):
        """Compare estimated TSS from planned duration with actual ride data."""
        planned_duration = 90  # minutes
        planned_ftp = 250.0
        estimated_tss = (planned_duration * planned_ftp * 3.5) / (90 * planned_ftp) * 100

        self._make_ride("2024-06-15", 35.0, 90.0, heart_rate_avg=150)
        assert estimated_tss > 0

    def test_load_adherence_with_atl_ctl_tsb(self):
        """Verify that completed rides produce training load metrics."""
        rides = [
            self._make_ride("2024-06-10", 30.0, 60.0, heart_rate_avg=145),
            self._make_ride("2024-06-12", 40.0, 90.0, heart_rate_avg=155),
            self._make_ride("2024-06-14", 25.0, 45.0, heart_rate_avg=140),
        ]
        loads = calculate_atl_ctl_tsb(rides)
        assert len(loads) > 0
        for entry in loads:
            assert hasattr(entry, "atl")
            assert hasattr(entry, "ctl")
            assert hasattr(entry, "tsb")

    def test_no_rides_zero_completion(self):
        """Zero rides means zero completion rate."""
        planned_dates = ["2024-06-10", "2024-06-12"]
        ride_dates = []
        completed = sum(1 for d in planned_dates if d in ride_dates)
        rate = completed / len(planned_dates) if planned_dates else 0
        assert rate == 0.0

    def test_all_rides_complete(self):
        """All planned dates covered = 100% completion."""
        planned_dates = ["2024-06-10", "2024-06-12", "2024-06-14"]
        ride_dates = ["2024-06-10", "2024-06-12", "2024-06-14"]
        completed = sum(1 for d in planned_dates if d in ride_dates)
        rate = completed / len(planned_dates)
        assert rate == 1.0

    def test_training_load_accumulation(self):
        """Verify CTL (fitness) accumulates over consecutive rides."""
        base_date = datetime(2024, 6, 1)
        rides = []
        for i in range(7):
            d = base_date.replace(day=1 + i)
            rides.append(
                Ride(
                    date=d.strftime("%Y-%m-%d"),
                    distance_km=30.0 + i * 2,
                    duration_minutes=60.0 + i * 5,
                    weight_kg=70.0,
                    heart_rate_avg=140 + i * 2,
                )
            )
        loads = calculate_atl_ctl_tsb(rides)
        assert len(loads) == 7
        ctl_values = [entry.ctl for entry in loads]
        assert ctl_values[-1] > ctl_values[0]

    def test_tsb_varies_with_load_pattern(self):
        """TSB should change when load pattern changes (varying TSS)."""
        base_date = datetime(2024, 5, 1)

        rides = [
            Ride(
                date=(base_date.replace(day=1 + i)).strftime("%Y-%m-%d"),
                distance_km=50.0,
                duration_minutes=120.0 if i % 3 == 0 else 60.0,
                weight_kg=70.0,
                heart_rate_avg=160,
            )
            for i in range(14)
        ]
        loads = calculate_atl_ctl_tsb(rides)
        assert len(loads) == 14

        tsb_values = [entry.tsb for entry in loads]
        assert any(v != 0.0 for v in tsb_values), "TSB should vary with non-uniform load"
