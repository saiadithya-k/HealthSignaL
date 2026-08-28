import math
import numpy as np
from datetime import datetime, timedelta
from typing import Dict

def compute_daily_base_demand(
    current_date: datetime,
    start_date: datetime,
    base_volume: float,
    day_of_week_multipliers: Dict[int, float],
    seasonality_amplitude: float,
    seasonality_phase_days: int,
    trend_rate_per_year: float = 0.02
) -> float:
    """Calculates deterministic expected daily demand before category breakdown and stochastic noise."""
    day_index = (current_date - start_date).days
    day_of_week = current_date.weekday()
    
    # 1. Day of week multiplier
    dow_mult = day_of_week_multipliers.get(day_of_week, 1.0)
    
    # 2. Annual seasonality (365.25 days cycle)
    day_of_year = current_date.timetuple().tm_yday
    seasonality_mult = 1.0 + seasonality_amplitude * math.sin(
        2 * math.pi * (day_of_year - seasonality_phase_days) / 365.25
    )
    
    # 3. Linear long-term trend
    trend_mult = 1.0 + (trend_rate_per_year * (day_index / 365.25))
    
    expected_demand = base_volume * dow_mult * seasonality_mult * trend_mult
    return max(1.0, expected_demand)


def partition_demand_by_syndrome(
    total_demand: float,
    syndrome_ratios: Dict[str, float],
    noise_std: float,
    rng: np.random.RandomState
) -> Dict[str, int]:
    """Partitions expected total demand into discrete counts across syndrome categories with noise."""
    counts = {}
    total_ratio = sum(syndrome_ratios.values())
    
    for category, ratio in syndrome_ratios.items():
        norm_ratio = ratio / total_ratio
        expected_cat_demand = total_demand * norm_ratio
        
        # Add zero-mean Gaussian noise scaled by noise_std
        noise = rng.normal(0, noise_std * math.sqrt(norm_ratio))
        cat_count = int(round(max(0, expected_cat_demand + noise)))
        counts[category] = cat_count
        
    return counts
