"""
STEP 3: Feature Engineering
Expand seed data (1 row/zone) → full dataset (multiple rows per zone × time)

For CNN-LSTM we need temporal sequences.
Each row = one zone at one specific time window.

Final feature set (12 features):
  1.  zone_id (categorical)
  2.  lat
  3.  lng
  4.  hour_of_day (0-23)
  5.  day_of_week (0=Mon, 6=Sun)
  6.  is_weekend (binary)
  7.  crime_count_normalized (historical, per zone)
  8.  police_coverage_score (0-1)
  9.  street_light_score (0-1)
  10. metro_access_score (0-1)
  11. footfall_score (0-1, time-dependent)
  12. sentiment_score (0-1, simulated NLP output)
  →   safety_score (TARGET, 0-100)
"""

import pandas as pd
import numpy as np

# Time risk weights — researched from crime pattern literature
# Higher = more risky time slot
TIME_RISK_WEIGHTS = {
    # hour : risk_multiplier
    0 : 1.8,   # 12am - very high risk
    1 : 1.9,
    2 : 2.0,   # 2am - highest risk
    3 : 1.9,
    4 : 1.7,
    5 : 1.4,
    6 : 1.1,
    7 : 0.8,
    8 : 0.7,   # morning commute - moderate
    9 : 0.6,
    10: 0.5,
    11: 0.5,
    12: 0.6,   # noon
    13: 0.6,
    14: 0.6,
    15: 0.6,
    16: 0.7,
    17: 0.8,   # evening commute starts
    18: 0.9,
    19: 1.0,
    20: 1.1,
    21: 1.2,
    22: 1.5,   # late night
    23: 1.7,
}

DAY_RISK_WEIGHTS = {
    0: 0.9,   # Monday
    1: 0.9,   # Tuesday
    2: 0.9,   # Wednesday
    3: 0.9,   # Thursday
    4: 1.1,   # Friday (higher)
    5: 1.3,   # Saturday (highest)
    6: 1.0,   # Sunday
}

def simulate_sentiment_score(zone_name: str, hour: int, crime_count: float) -> float:
    """
    Simulate what NLP module would output as sentiment score (0-1).
    0 = very negative/unsafe sentiment, 1 = positive/safe sentiment.
    In production, this comes from Twitter/X NLP module.
    """
    # High crime zones tend to have more negative sentiment online
    crime_normalized = min(crime_count / 300, 1.0)
    base_sentiment = 1.0 - (crime_normalized * 0.6)
    
    # Late night = more distress tweets
    if hour >= 22 or hour <= 4:
        base_sentiment -= 0.15
    
    noise = np.random.uniform(-0.1, 0.1)
    return round(max(0.0, min(1.0, base_sentiment + noise)), 3)

def compute_safety_score(row: dict) -> float:
    """
    SAFETY SCORE FORMULA (0-100):
    
    This is the TARGET variable — the label for your ML model.
    
    Formula:
      Raw = (
          police_coverage     × 0.20  [infrastructure]
        + street_light         × 0.15  [infrastructure]
        + metro_access         × 0.10  [infrastructure]
        + footfall             × 0.10  [environment]
        + sentiment            × 0.20  [social signals]
        + inverse_crime        × 0.15  [historical crime]
        + inverse_time_risk    × 0.10  [temporal risk]
      ) × 100
    
    Academic basis: Expert-driven composite label synthesis
    (validated in Kumar et al. 2023, INNS paper from your references)
    """
    time_risk    = TIME_RISK_WEIGHTS.get(int(row['hour_of_day']), 1.0)
    day_risk     = DAY_RISK_WEIGHTS.get(int(row['day_of_week']), 1.0)
    
    # Normalize crime count: max observed Delhi zone annual ~ 350
    crime_norm   = min(row['crime_count_normalized'], 1.0)
    
    # Inverse: low crime → high score
    inverse_crime     = 1.0 - crime_norm
    # Inverse time risk: max time_risk=2.0, normalize to 0-1 and invert
    inverse_time_risk = 1.0 - min((time_risk * day_risk - 0.5) / 2.0, 1.0)
    
    raw_score = (
        row['police_coverage_score'] * 0.20 +
        row['street_light_score']    * 0.15 +
        row['metro_access_score']    * 0.10 +
        row['footfall_score']        * 0.10 +
        row['sentiment_score']       * 0.20 +
        inverse_crime                * 0.15 +
        inverse_time_risk            * 0.10
    )
    
    # Scale to 0-100 and add small noise for realism
    score = (raw_score * 100) + np.random.uniform(-3, 3)
    return round(max(0.0, min(100.0, score)), 2)

def generate_time_expanded_dataset(seed_df: pd.DataFrame, 
                                    hours_per_zone: int = 168) -> pd.DataFrame:
    """
    Expand seed data (1 row/zone) → time-series dataset
    
    hours_per_zone = 168 means one full week (24h × 7 days) per zone
    With 70 zones × 168 time slots = 11,760 rows (good for training)
    
    For larger dataset: multiply by multiple weeks
    """
    rows = []
    max_crime = seed_df['annual_crime_count'].max()
    
    for _, zone in seed_df.iterrows():
        crime_normalized = zone['annual_crime_count'] / max_crime
        
        for week in range(4):  # 4 weeks = 70 × 168 × 4 = 47,040 rows
            for day in range(7):
                for hour in range(24):
                    footfall = _compute_footfall(zone['zone_name'], hour, day)
                    sentiment = simulate_sentiment_score(
                        zone['zone_name'], hour, zone['annual_crime_count']
                    )
                    
                    row = {
                        'zone_id'               : zone['zone_id'],
                        'zone_name'             : zone['zone_name'],
                        'lat'                   : zone['lat'],
                        'lng'                   : zone['lng'],
                        'district'              : zone['district'],
                        'zone_type'             : zone['zone_type'],
                        'hour_of_day'           : hour,
                        'day_of_week'           : day,
                        'is_weekend'            : int(day >= 5),
                        'crime_count_normalized': round(crime_normalized, 4),
                        'police_coverage_score' : zone['police_coverage_score'],
                        'street_light_score'    : zone['street_light_score'],
                        'metro_access_score'    : zone['metro_access_score'],
                        'footfall_score'        : footfall,
                        'sentiment_score'       : sentiment,
                    }
                    row['safety_score'] = compute_safety_score(row)
                    rows.append(row)
    
    df = pd.DataFrame(rows)
    print(f"✅ Time-expanded dataset: {len(df):,} rows × {len(df.columns)} features")
    return df

def _compute_footfall(zone_name: str, hour: int, day: int) -> float:
    from step2_seed_data import INFRASTRUCTURE_SEED
    is_high = zone_name in INFRASTRUCTURE_SEED["high_night_footfall"]
    
    if 10 <= hour <= 21:
        base = 0.75 if is_high else 0.50
    elif hour >= 22 or hour <= 4:
        base = 0.30 if is_high else 0.10
    else:
        base = 0.45 if is_high else 0.30
    
    # Weekend boost
    if day >= 5:
        base += 0.10
    
    return round(max(0.0, min(1.0, base + np.random.uniform(-0.05, 0.05))), 3)

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/home/claude/safeher_dataset')
    from step1_zones import create_zones_dataframe
    from step2_seed_data import build_seed_data
    
    zones_df = create_zones_dataframe()
    seed_df  = build_seed_data(zones_df)
    
    full_df  = generate_time_expanded_dataset(seed_df)
    full_df.to_csv('delhi_features_raw.csv', index=False)
    
    print("\n── Feature Summary ──")
    print(full_df.describe())
    print(f"\nSafety Score Distribution:")
    print(full_df['safety_score'].describe())
    
    # Show a sample
    print("\nSample rows:")
    print(full_df[full_df['zone_name'] == 'Chandni Chowk'][
        ['zone_name','hour_of_day','day_of_week','safety_score']
    ].head(10))
