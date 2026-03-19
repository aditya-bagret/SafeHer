"""
STEP 5: Combine Real + Synthetic Data → Final CNN-LSTM Ready Dataset

This step:
  1. Merges real and synthetic rows
  2. Encodes categoricals
  3. Normalizes all features
  4. Creates temporal sequences (needed for CNN-LSTM)
  5. Exports train/test splits
  6. Prints final dataset summary for your paper
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import json

def build_final_dataset(real_df: pd.DataFrame, 
                        synthetic_df: pd.DataFrame) -> pd.DataFrame:
    """Merge and clean the combined dataset"""
    
    # Tag sources
    real_df = real_df.copy()
    synthetic_df = synthetic_df.copy()
    real_df['data_source']      = 'real_seed'
    synthetic_df['data_source'] = 'synthetic'
    
    # Attach zone metadata to synthetic rows (assign randomly from real zones)
    # This allows groupby-per-zone to work for sequence creation
    if 'zone_name' not in synthetic_df.columns:
        zone_names = real_df['zone_name'].unique()
        synthetic_df['zone_name'] = np.random.choice(zone_names, size=len(synthetic_df))
    if 'zone_id' not in synthetic_df.columns:
        synthetic_df['zone_id'] = synthetic_df['zone_name'].apply(
            lambda z: real_df.loc[real_df['zone_name'] == z, 'zone_id'].iloc[0]
            if z in real_df['zone_name'].values else 'SYNTH'
        )
    
    # Align columns between real and synthetic
    common_cols = [c for c in real_df.columns if c in synthetic_df.columns]
    
    # Combine
    combined = pd.concat([
        real_df[common_cols],
        synthetic_df[common_cols]
    ], ignore_index=True)
    
    print(f"✅ Combined dataset: {len(combined):,} rows")
    print(f"   Real rows    : {(combined['data_source']=='real_seed').sum():,}")
    print(f"   Synthetic    : {(combined['data_source']=='synthetic').sum():,}")
    
    return combined

def encode_and_normalize(df: pd.DataFrame) -> tuple:
    """Encode categoricals, normalize numerics"""
    
    processed = df.copy()
    
    # Keep zone_name for sequence grouping (not a model feature)
    if 'zone_name' in processed.columns:
        pass  # keep it
    
    # --- Encode zone_type ---
    zone_type_map = {'Commercial': 2, 'Residential': 1, 'Industrial': 1.5}
    if 'zone_type' in processed.columns:
        processed['zone_type_encoded'] = processed['zone_type'].map(zone_type_map).fillna(1)
    
    # --- Encode district as integer ---
    if 'district' in processed.columns:
        le = LabelEncoder()
        processed['district_encoded'] = le.fit_transform(processed['district'])
    
    # --- Feature columns for model ---
    feature_cols = [
        'hour_of_day',
        'day_of_week',
        'is_weekend',
        'crime_count_normalized',
        'police_coverage_score',
        'street_light_score',
        'metro_access_score',
        'footfall_score',
        'sentiment_score',
        'zone_type_encoded',
        'district_encoded',
    ]
    
    target_col = 'safety_score'
    
    # Keep only available features
    feature_cols = [c for c in feature_cols if c in processed.columns]
    
    # Normalize features to [0, 1]
    scaler = MinMaxScaler()
    processed[feature_cols] = scaler.fit_transform(processed[feature_cols])
    
    print(f"✅ Encoded & normalized {len(feature_cols)} features")
    print(f"   Features: {feature_cols}")
    
    return processed, feature_cols, target_col, scaler

def create_cnn_lstm_sequences(df: pd.DataFrame, 
                               feature_cols: list,
                               target_col: str,
                               sequence_length: int = 24) -> tuple:
    """
    Create temporal sequences for CNN-LSTM.
    
    CNN-LSTM needs 3D input: (samples, timesteps, features)
    
    sequence_length=24 means: for each prediction point,
    use the past 24 hours of data as input window.
    
    This mimics the paper's tensor: X ∈ R^(n × t × f)
    where n=samples, t=24 (time steps), f=num features
    """
    X_sequences = []
    y_labels    = []
    zone_ids    = []
    
    # Sort by zone, then by time (day × 24 + hour)
    sort_cols = [c for c in ['zone_name', 'day_of_week', 'hour_of_day'] if c in df.columns]
    df_sorted = df.sort_values(sort_cols) if sort_cols else df
    
    group_col = 'zone_name' if 'zone_name' in df.columns else 'zone_id'
    for zone_name, zone_data in df_sorted.groupby(group_col):
        zone_data = zone_data.reset_index(drop=True)
        features  = zone_data[feature_cols].values
        targets   = zone_data[target_col].values
        
        # Sliding window sequences
        for i in range(sequence_length, len(features)):
            X_sequences.append(features[i-sequence_length:i])  # shape: (24, 11)
            y_labels.append(targets[i])
            zone_ids.append(zone_name)
    
    X = np.array(X_sequences)  # shape: (num_sequences, 24, 11)
    y = np.array(y_labels)
    
    print(f"\n✅ Sequence creation complete:")
    print(f"   X shape (samples × timesteps × features): {X.shape}")
    print(f"   y shape (target values)                 : {y.shape}")
    print(f"   = {X.shape[0]:,} training samples for CNN-LSTM")
    
    return X, y, zone_ids

def export_final_dataset(df: pd.DataFrame, 
                         X: np.ndarray, 
                         y: np.ndarray,
                         feature_cols: list):
    """Split into train/test and export everything"""
    
    # Train/Test split: 80/20 (as per CNN-LSTM paper)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, shuffle=True
    )
    
    print(f"\n── Final Dataset Split ──")
    print(f"   Train sequences : {X_train.shape[0]:,}")
    print(f"   Test sequences  : {X_test.shape[0]:,}")
    print(f"   Input shape     : {X_train.shape}")
    
    # Save numpy arrays for direct model training
    np.save('X_train.npy', X_train)
    np.save('X_test.npy',  X_test)
    np.save('y_train.npy', y_train)
    np.save('y_test.npy',  y_test)
    
    # Save flat CSV for exploratory analysis / other models
    df.to_csv('delhi_final_dataset.csv', index=False)
    
    # Save metadata
    metadata = {
        'dataset_name'     : 'SafeHer Delhi Safety Dataset v1.0',
        'total_rows'       : len(df),
        'total_sequences'  : len(X),
        'num_features'     : len(feature_cols),
        'feature_names'    : feature_cols,
        'target_variable'  : 'safety_score',
        'target_range'     : '0-100',
        'sequence_length'  : 24,
        'zones_covered'    : df['zone_name'].nunique() if 'zone_name' in df.columns else 'N/A',
        'city'             : 'Delhi, India',
        'data_sources'     : ['NCRB 2022 (seed)', 'Infrastructure proxies', 'CTGAN synthetic augmentation'],
        'train_test_split' : '80/20',
        'input_tensor'     : f'({X_train.shape[0]}, {X_train.shape[1]}, {X_train.shape[2]})',
    }
    
    with open('dataset_metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n✅ All files saved:")
    print(f"   delhi_final_dataset.csv     — flat CSV for analysis")
    print(f"   X_train.npy / X_test.npy    — CNN-LSTM input arrays")
    print(f"   y_train.npy / y_test.npy    — target arrays")
    print(f"   dataset_metadata.json       — dataset documentation")
    
    return X_train, X_test, y_train, y_test

def print_paper_summary(df: pd.DataFrame, X: np.ndarray, feature_cols: list):
    """Print the dataset description for your research paper"""
    print("\n" + "="*60)
    print("PAPER-READY DATASET DESCRIPTION")
    print("="*60)
    print(f"""
Dataset: SafeHer Delhi Women Safety Dataset
City   : New Delhi, India
Zones  : {df['zone_name'].nunique() if 'zone_name' in df else 'N/A'} geographic zones
Rows   : {len(df):,} total records
        ({(df['data_source']=='real_seed').sum():,} real seed + {(df['data_source']=='synthetic').sum():,} CTGAN synthetic)

Features ({len(feature_cols)}):
  Temporal   : hour_of_day, day_of_week, is_weekend
  Historical : crime_count_normalized (NCRB 2022)
  Infra      : police_coverage_score, street_light_score, metro_access_score
  Social     : footfall_score, sentiment_score (simulated NLP)
  Encoded    : zone_type_encoded, district_encoded

Target     : safety_score (0–100, composite label)
CNN-LSTM   : X tensor shape = {X.shape} (n × t × f)

Methodology: 
  Expert-driven label synthesis + CTGAN augmentation
  80/20 train-test split, MinMaxScaler normalization
""")

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/home/claude/safeher_dataset')
    from step1_zones import create_zones_dataframe
    from step2_seed_data import build_seed_data
    from step3_feature_engineering import generate_time_expanded_dataset
    from step4_ctgan_synthesis import generate_synthetic_data_ctgan, validate_synthetic_data
    
    print("="*50)
    print("SafeHer Dataset Pipeline — Full Run")
    print("="*50)
    
    # Steps 1-3: Real data
    zones_df  = create_zones_dataframe()
    seed_df   = build_seed_data(zones_df)
    real_df   = generate_time_expanded_dataset(seed_df)
    
    # Step 4: Synthetic augmentation
    synthetic_df = generate_synthetic_data_ctgan(real_df, num_synthetic_rows=15000)
    validate_synthetic_data(real_df, synthetic_df)
    
    # Step 5: Finalize
    combined_df, feature_cols, target_col, scaler = encode_and_normalize(
        build_final_dataset(real_df, synthetic_df)
    )
    
    X, y, zone_ids = create_cnn_lstm_sequences(combined_df, feature_cols, target_col)
    
    X_train, X_test, y_train, y_test = export_final_dataset(
        combined_df, X, y, feature_cols
    )
    
    print_paper_summary(combined_df, X, feature_cols)