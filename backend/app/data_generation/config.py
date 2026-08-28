from typing import Dict, Any

INSTITUTION_PROFILES: Dict[str, Dict[str, Any]] = {
    "inst-a": {
        "id": "inst-a",
        "name": "Institution A",
        "profile": "Urban (High Volume)",
        "base_volume": 140.0,
        "syndrome_ratios": {
            "respiratory": 0.40,
            "gastrointestinal": 0.25,
            "fever_flu": 0.20,
            "other": 0.15
        },
        "day_of_week_multipliers": {
            0: 1.20,  # Monday peak
            1: 1.15,
            2: 1.10,
            3: 1.05,
            4: 1.00,
            5: 0.75,  # Saturday drop
            6: 0.75   # Sunday drop
        },
        "seasonality_amplitude": 0.15,
        "seasonality_phase_days": 15,  # Winter peak
        "noise_std": 6.0
    },
    "inst-b": {
        "id": "inst-b",
        "name": "Institution B",
        "profile": "Semi-urban (Moderate Volume)",
        "base_volume": 85.0,
        "syndrome_ratios": {
            "respiratory": 0.20,
            "gastrointestinal": 0.45,  # Gastro heavy
            "fever_flu": 0.25,
            "other": 0.10
        },
        "day_of_week_multipliers": {
            0: 1.02,
            1: 1.00,
            2: 0.98,
            3: 1.02,
            4: 1.00,
            5: 0.99,
            6: 0.99
        },
        "seasonality_amplitude": 0.25,
        "seasonality_phase_days": 180, # Summer peak for gastro
        "noise_std": 9.0
    },
    "inst-c": {
        "id": "inst-c",
        "name": "Institution C",
        "profile": "Rural (Low Volume, High Variance)",
        "base_volume": 28.0,
        "syndrome_ratios": {
            "respiratory": 0.15,
            "gastrointestinal": 0.15,
            "fever_flu": 0.55,        # Fever/Flu heavy
            "other": 0.15
        },
        "day_of_week_multipliers": {
            0: 0.85,
            1: 0.85,
            2: 0.90,
            3: 0.95,
            4: 1.00,
            5: 1.30,  # Weekend clinic spike
            6: 1.25
        },
        "seasonality_amplitude": 0.35,
        "seasonality_phase_days": 340, # Late autumn peak
        "noise_std": 7.0
    },
    "inst-d": {
        "id": "inst-d",
        "name": "Institution D",
        "profile": "Mixed (Seasonal Shift)",
        "base_volume": 105.0,
        "syndrome_ratios": {
            "respiratory": 0.30,
            "gastrointestinal": 0.30,
            "fever_flu": 0.25,
            "other": 0.15
        },
        "day_of_week_multipliers": {
            0: 0.95,
            1: 1.00,
            2: 1.15,  # Midweek peak
            3: 1.15,
            4: 1.05,
            5: 0.85,
            6: 0.85
        },
        "seasonality_amplitude": 0.20,
        "seasonality_phase_days": 60,
        "noise_std": 12.0
    }
}
