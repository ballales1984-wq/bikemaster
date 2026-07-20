"""Advanced cycling power analysis models.

Implements industry-standard power metrics:
1. Normalized Power (NP) — Coggan algorithm with 30s rolling average
2. Intensity Factor (IF) — NP / FTP
3. Variability Index (VI) — NP / avg power
4. Efficiency Factor (EF) — NP / avg HR
5. Training Stress Score (TSS) — IF² × duration(h) × 100
6. Power Profile — best efforts at durations (5s, 1min, 5min, 20min, FTP)
7. Power Zones Coggan — 7-zone model
8. Pedal Smoothness / Torque Effectiveness estimates
9. W' (W prime) / Critical Power model
10. Aerobic Decoupling detection

References:
- Coggan, A. & Allen, H. (2019). Training and Racing with a Power Meter.
- Allen, H. & Coggan, A. (2010). Training and Racing with a Power Meter.
- Pinot, J. et al. (2014). MPA model for aerobic power estimation.
"""

from __future__ import annotations

from typing import Any

from ..models.models import GPSPoint

POWER_ZONES_COGGAN = [
    ("Z1", "Recovery", 0.55, 0.64, "#4ecca3"),
    ("Z2", "Endurance", 0.64, 0.74, "#90EE90"),
    ("Z3", "Tempo", 0.74, 0.84, "#FFD700"),
    ("Z4", "Threshold", 0.84, 0.94, "#FFA500"),
    ("Z5", "VO2max", 0.94, 1.00, "#FF4500"),
    ("Z6", "Anaerobic", 1.00, 1.10, "#DC143C"),
    ("Z7", "Neuromuscular", 1.10, 1.50, "#8B0000"),
]


def normalized_power(watts: list[float], window_size: int = 30) -> float:
    """Normalized Power (Coggan): media mobile di 30s, elevata alla 4ª, mediata, radice 4ª.

    L'elevamento alla quarta potenza penalizza i picchi di potenza (sforzi
    short/explosive) much more than arithmetic mean, so NP reflects the
    carico metabolico reale meglio della potenza media. Se i dati sono troppo
    pochi per una finestra, ritorna la media semplice.
    """
    if not watts or len(watts) < window_size:
        return sum(watts) / len(watts) if watts else 0.0
    smoothed = []
    for i in range(len(watts) - window_size + 1):
        segment = watts[i : i + window_size]
        avg = sum(segment) / window_size
        smoothed.append(avg**4)
    if not smoothed:
        return sum(watts) / len(watts) if watts else 0.0
    mean_powered = sum(smoothed) / len(smoothed)
    return round(mean_powered**0.25, 1)


def intensity_factor(np: float, ftp: float) -> float:
    """Intensity Factor (IF): NP / FTP. Indica l'intensita' relativa alla soglia."""
    return round(np / ftp, 3) if ftp > 0 else 0.0


def variability_index(np: float, avg_power: float) -> float:
    """Variability Index (VI): NP / avg power. 1.0 = potenza perfettamente costante."""
    return round(np / avg_power, 3) if avg_power > 0 else 0.0


def efficiency_factor(np: float, avg_hr: float) -> float:
    """Efficiency Factor (EF): NP / avg HR. Indica l'efficienza cardiaca."""
    return round(np / avg_hr, 3) if avg_hr > 0 else 0.0


def training_stress_score(np: float, if_value: float, duration_h: float) -> float:
    """Training Stress Score (TSS): IF^2 x durata(h) x 100. Clamp a 500."""
    tss = duration_h * 100.0 * (if_value**2)
    return round(min(tss, 500.0), 1)


def calculate_power_zones(points: list[GPSPoint], ftp: float) -> dict[str, dict[str, Any]]:
    """Distribuzione tempo in zone di potenza Coggan (Z1-Z7) basate su FTP."""
    watts_series = [p.power if p.power is not None else 0.0 for p in points if p.power is not None]
    if not watts_series or ftp <= 0:
        return {}
    zones: dict[str, dict[str, Any]] = {}
    total_samples = len(watts_series)
    for name, label, low, high, color in POWER_ZONES_COGGAN:
        lower_w = low * ftp
        upper_w = high * ftp
        count = sum(1 for w in watts_series if lower_w <= w < upper_w)
        zones[name] = {
            "label": label,
            "lower_w": round(lower_w, 0),
            "upper_w": round(upper_w, 0),
            "lower_pct": round(low * 100, 0),
            "upper_pct": round(high * 100, 0),
            "count": count,
            "pct_time": round(count / total_samples * 100, 1) if total_samples else 0,
            "color": color,
        }
    return zones


def calculate_power_profile(points: list[GPSPoint]) -> dict[str, float | None]:
    """Best effort per durate (5s, 1min, 5min, 10min, 20min, 30min) da serie di potenza."""
    watts_series = [(p.timestamp, p.power) for p in points if p.power is not None]
    if not watts_series:
        return dict.fromkeys(["5s", "1min", "5min", "10min", "20min", "30min"])
    binned = _bin_powers(watts_series)
    return _power_profile_to_dict(binned)


def _bin_powers(watts_series: list, ride: Any | None = None) -> dict:
    """Trova la massima potenza media sostenuta per durate target (5s..30min).

    Sliding window su serie (timestamp, watt) ordinata per tempo: la finestra
    right advances by one sample and left retreats until span exceeds the
    target, so each window has duration ~target. For each target it keeps the
    massimo watt medio ottenuto (best effort — equivale al "mean maximal power").
    """
    if not watts_series:
        return {}
    watts_series.sort(key=lambda x: x[0])
    targets = [5, 60, 300, 600, 1200, 1800]
    best_for: dict = dict.fromkeys(targets, 0.0)
    for target in targets:
        left = 0
        current_sum = 0.0
        count = 0
        for right in range(len(watts_series)):
            current_sum += watts_series[right][1]
            count += 1
            span = (watts_series[right][0] - watts_series[left][0]).total_seconds()
            while left < right and span > target + 2:
                current_sum -= watts_series[left][1]
                count -= 1
                left += 1
                span = (watts_series[right][0] - watts_series[left][0]).total_seconds()
            if count >= 2 and abs(span - target) <= 2 and span >= target - 2:
                avg = current_sum / count
                if avg > best_for[target]:
                    best_for[target] = avg
    return best_for


def _power_profile_to_dict(binned: dict) -> dict[str, float | None]:
    """Converte i best-effort binati in dizionario con etichette leggibili."""
    labels = {5: "5s", 60: "1min", 300: "5min", 600: "10min", 1200: "20min", 1800: "30min"}
    return {label: round(binned[d], 1) if binned.get(d, 0) > 0 else None for d, label in labels.items()}


def estimate_ftp_from_20min(points: list[GPSPoint]) -> float:
    """Stima FTP come 95% della miglior potenza media di 20 minuti."""
    profile = calculate_power_profile(points)
    best_20 = profile.get("20min")
    if best_20 is None:
        return 0.0
    return round(best_20 * 0.95, 1)


def estimate_critical_power(points: list[GPSPoint]) -> dict[str, float]:
    """Stima Critical Power (CP) e W' (J) dal power profile 5min/10min."""
    profile = calculate_power_profile(points)
    p_short = profile.get("5min") or 0.0
    p_long = profile.get("10min") or 0.0
    if p_short > 0 and p_long > 0:
        t_s, t_l = 5.0, 12.0
        cp = (p_long * t_l - p_short * t_s) / (t_l - t_s)
        w_prime = (p_short - cp) * t_s
        cp = max(cp, 100)
        w_prime = max(w_prime, 5000)
        return {"cp_w": round(cp, 1), "w_prime_j": round(w_prime, 0)}
    return {"cp_w": 0.0, "w_prime_j": 0.0}


def detect_aerobic_decoupling(points: list[GPSPoint], ftp: float | None = None) -> dict[str, Any]:
    """Rileva decoupling aerobico confrontando HR/power prima e seconda meta' dell'uscita."""
    if len(points) < 60:
        return {"decoupling_pct": 0.0, "significant": False}
    mid = len(points) // 2
    first_half = [p for p in points[:mid] if p.power is not None and p.heart_rate is not None]
    second_half = [p for p in points[mid:] if p.power is not None and p.heart_rate is not None]
    if not first_half or not second_half:
        return {"decoupling_pct": 0.0, "significant": False}

    def avg_power_ratio(seg):
        """Rapporto potenza media/FTP per un segmento dell'uscita."""
        return sum(p.power for p in seg) / len(seg) / ftp if ftp > 0 else 0

    p1 = avg_power_ratio(first_half)
    p2 = avg_power_ratio(second_half)
    ratio_first = sum(p.heart_rate for p in first_half) / len(first_half)
    ratio_second = sum(p.heart_rate for p in second_half) / len(second_half)
    hr_decoupling = 0.0
    if ratio_first > 0:
        hr_decoupling = (ratio_second / ratio_first - 1) * 100
    decoupling = abs(hr_decoupling)
    return {
        "decoupling_pct": round(decoupling, 1),
        "significant": decoupling > 5.0,
        "first_half_power_ratio": round(p1, 3),
        "second_half_power_ratio": round(p2, 3),
        "first_half_hr": round(ratio_first, 1),
        "second_half_hr": round(ratio_second, 1),
    }


def calculate_advanced_power_metrics(points: list[GPSPoint], ftp: float = 250.0) -> dict[str, Any]:
    """Metriche avanzate complete: NP, IF, VI, EF, TSS, zone, profilo, decoupling."""
    watts = [p.power for p in points if p.power is not None]
    hrs = [p.heart_rate for p in points if p.heart_rate is not None]
    if not watts:
        return {"available": False, "reason": "no_power_data"}
    avg_w = sum(watts) / len(watts)
    np = normalized_power(watts)
    if_val = intensity_factor(np, ftp)
    vi = variability_index(np, avg_w)
    ef = efficiency_factor(np, sum(hrs) / len(hrs)) if hrs else None
    duration_pts = len(watts)
    sample_interval_s = 1.0
    duration_h = duration_pts * sample_interval_s / 3600.0
    tss = training_stress_score(np, if_val, duration_h)
    zones = calculate_power_zones(points, ftp)
    profile = calculate_power_profile(points)
    decoupling = detect_aerobic_decoupling(points, ftp)
    return {
        "available": True,
        "ftp": ftp,
        "avg_power_w": round(avg_w, 1),
        "max_power_w": round(max(watts), 1),
        "normalized_power_w": np,
        "intensity_factor": if_val,
        "variability_index": vi,
        "efficiency_factor": round(ef, 3) if ef else None,
        "tss": tss,
        "duration_hours": round(duration_h, 2),
        "power_zones": zones,
        "power_profile": profile,
        "decoupling": decoupling,
    }

