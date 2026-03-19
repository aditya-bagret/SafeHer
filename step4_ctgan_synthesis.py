"""
STEP 4: Synthetic Data Generation using CTGAN
(Conditional Tabular GAN)

Why CTGAN over simple random noise:
  - Learns real statistical distributions from seed data
  - Preserves correlations (e.g. high crime zone + night = low safety)
  - Handles mixed data types (categorical + numerical)
  - Used in multiple IEEE papers for safety dataset augmentation

Install: pip install ctgan sdv
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

def generate_synthetic_data_ctgan(real_df: pd.DataFrame, 
                                   num_synthetic_rows: int = 10000) -> pd.DataFrame:
    """
    Train CTGAN on real feature data and generate synthetic rows.
    
    Input:  real_df — your feature-engineered dataset from Step 3
    Output: synthetic_df — statistically similar but new rows
    """
    try:
        from ctgan import CTGAN
        print("✅ CTGAN loaded")
        use_ctgan = True
    except ImportError:
        print("⚠️  CTGAN not installed. Using fallback statistical sampling.")
        print("   Install with: pip install ctgan sdv")
        use_ctgan = False
    
    # Columns to use for CTGAN training (numeric features only)
    numeric_features = [
        'hour_of_day', 'day_of_week', 'is_weekend',
        'crime_count_normalized', 'police_coverage_score',
        'street_light_score', 'metro_access_score',
        'footfall_score', 'sentiment_score', 'safety_score'
    ]
    
    # Categorical columns that CTGAN handles specially
    discrete_columns = ['hour_of_day', 'day_of_week', 'is_weekend']
    
    train_df = real_df[numeric_features].copy()
    
    if use_ctgan:
        print(f"🔄 Training CTGAN on {len(train_df):,} rows...")
        model = CTGAN(
            epochs=300,          # More epochs = better quality (use 500 for final)
            batch_size=500,
            verbose=True
        )
        model.fit(train_df, discrete_columns)
        
        print(f"🔄 Generating {num_synthetic_rows:,} synthetic rows...")
        synthetic_df = model.sample(num_synthetic_rows)
        
    else:
        # Fallback: Bootstrap sampling with noise
        synthetic_df = _bootstrap_with_noise(train_df, num_synthetic_rows)
    
    return synthetic_df

def _bootstrap_with_noise(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """
    Fallback if CTGAN not installed.
    Statistical bootstrap sampling + Gaussian noise.
    Not as good as CTGAN but still valid for dataset augmentation.
    """
    print(f"🔄 Bootstrap sampling {n:,} rows...")
    sampled = df.sample(n=n, replace=True).copy().reset_index(drop=True)
    
    # Add Gaussian noise to continuous features
    continuous = [
        'crime_count_normalized', 'police_coverage_score',
        'street_light_score', 'metro_access_score',
        'footfall_score', 'sentiment_score'
    ]
    for col in continuous:
        std = df[col].std() * 0.15  # 15% noise
        noise = np.random.normal(0, std, n)
        sampled[col] = (sampled[col] + noise).clip(0, 1)
    
    # Re-randomize time features
    sampled['hour_of_day'] = np.random.randint(0, 24, n)
    sampled['day_of_week'] = np.random.randint(0, 7, n)
    sampled['is_weekend']  = (sampled['day_of_week'] >= 5).astype(int)
    
    # Recompute safety_score based on noised features
    sampled['safety_score'] = sampled.apply(_recompute_score, axis=1)
    
    print(f"✅ Bootstrap sampling complete: {len(sampled):,} rows")
    return sampled

def _recompute_score(row) -> float:
    """Recompute safety score from Step 3 formula"""
    from step3_feature_engineering import TIME_RISK_WEIGHTS, DAY_RISK_WEIGHTS
    time_risk = TIME_RISK_WEIGHTS.get(int(row['hour_of_day']), 1.0)
    day_risk  = DAY_RISK_WEIGHTS.get(int(row['day_of_week']), 1.0)
    inverse_time = 1.0 - min((time_risk * day_risk - 0.5) / 2.0, 1.0)
    
    raw = (
        row['police_coverage_score'] * 0.20 +
        row['street_light_score']    * 0.15 +
        row['metro_access_score']    * 0.10 +
        row['footfall_score']        * 0.10 +
        row['sentiment_score']       * 0.20 +
        (1 - row['crime_count_normalized']) * 0.15 +
        inverse_time                 * 0.10
    )
    score = raw * 100 + np.random.uniform(-2, 2)
    return round(max(0.0, min(100.0, score)), 2)

def validate_synthetic_data(real_df: pd.DataFrame, 
                             synthetic_df: pd.DataFrame):
    """
    Statistical validation — check synthetic data matches real distributions.
    This is what you cite in your paper as 'synthetic data validation'.
    """
    print("\n── Statistical Validation ──")
    print(f"{'Feature':<30} {'Real Mean':>10} {'Synth Mean':>10} {'Real Std':>10} {'Synth Std':>10}")
    print("-" * 70)
    
    features = [
        'crime_count_normalized', 'police_coverage_score',
        'street_light_score', 'safety_score'
    ]
    for f in features:
        if f in real_df.columns and f in synthetic_df.columns:
            print(f"{f:<30} {real_df[f].mean():>10.3f} {synthetic_df[f].mean():>10.3f} "
                  f"{real_df[f].std():>10.3f} {synthetic_df[f].std():>10.3f}")
    
    print("\n✅ If means/stds are close, synthetic data is statistically valid.")

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/home/claude/safeher_dataset')
    
    # Load real data from Step 3
    real_df = pd.read_csv('delhi_features_raw.csv')
    print(f"Real dataset: {len(real_df):,} rows")
    
    # Generate synthetic data
    synthetic_df = generate_synthetic_data_ctgan(real_df, num_synthetic_rows=15000)
    
    # Validate
    validate_synthetic_data(real_df, synthetic_df)
    
    # Save
    synthetic_df.to_csv('delhi_synthetic_data.csv', index=False)
    print(f"\n✅ Synthetic data saved: {len(synthetic_df):,} rows")
