"""Test for metabolic reference means and adaptive weight calibration."""

from bike_analyzer.core.calculators.metabolism import (
    AdaptiveWeights,
    adapt_weights_from_delta,
    blended_expenditure,
    calibrate_weights,
    reference_for_athlete,
    sensor_confidence,
)


def test_reference_for_athlete_returns_bracket_means():
    ref = reference_for_athlete(age=35, sex="male", weight_kg=80.0, activity_level="moderate")
    assert ref["age_bracket"] == [30, 39]
    assert ref["weight_bracket"] == [75, 89]
    assert ref["bmr_kcal"] > 0
    assert ref["tdee_kcal"] > ref["bmr_kcal"]


def test_adapt_weights_from_delta_moves_toward_ratio():
    w = adapt_weights_from_delta(sensor_value=2200.0, reference_value=2000.0, current_weight=1.0, learning_rate=0.5, confidence=1.0)
    # target = 2200/2000 = 1.1, delta = (1.1-1.0)*0.5 = 0.05
    assert w == 1.05


def test_adapt_weights_damped_by_confidence():
    high = adapt_weights_from_delta(2200.0, 2000.0, current_weight=1.0, learning_rate=0.5, confidence=1.0)
    low = adapt_weights_from_delta(2200.0, 2000.0, current_weight=1.0, learning_rate=0.5, confidence=0.0)
    assert high > low
    assert low == 1.0


def test_sensor_confidence_high_when_close_to_reference():
    conf = sensor_confidence(2010.0, 2000.0, prior_confidence=0.5, learning_rate=0.5)
    assert conf > 0.5


def test_sensor_confidence_low_when_far_from_reference():
    conf = sensor_confidence(4000.0, 2000.0, prior_confidence=1.0, learning_rate=0.5)
    assert conf < 1.0


def test_calibrate_weights_updates_state_and_counts():
    weights = AdaptiveWeights()
    calibrated = calibrate_weights(weights, sensor_bmr=1900.0, sensor_tdee=2600.0, ref_bmr=2000.0, ref_tdee=2500.0)
    assert calibrated.n_updates == 1
    assert calibrated.activity_multiplier_w != 1.0
    assert 0.0 <= calibrated.sensor_tdee_conf <= 1.0


def test_blended_expenditure_uses_reference_when_no_sensor():
    weights = AdaptiveWeights()
    ref = {"bmr_kcal": 2000.0, "tdee_kcal": 2500.0}
    out = blended_expenditure(weights, ref)
    assert out["bmr_kcal"] == 2000.0
    assert out["tdee_kcal"] == 2500.0


def test_blended_expenditure_blends_sensor_with_confidence():
    weights = AdaptiveWeights(sensor_tdee_conf=0.5)
    ref = {"bmr_kcal": 2000.0, "tdee_kcal": 2500.0}
    sensor = {"bmr_kcal": 1800.0, "tdee_kcal": 2800.0}
    out = blended_expenditure(weights, ref, sensor)
    # 0.5*2800 + 0.5*2500 = 2650
    assert out["tdee_kcal"] == 2650.0
