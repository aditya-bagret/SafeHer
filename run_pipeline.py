# Quick fix — run this directly if you don't want to re-run the full pipeline
import pandas as pd, numpy as np, sys
sys.path.insert(0, '.')
from step5_finalize_export import *

real_df  = pd.read_csv('delhi_features_raw.csv')
synth_df = pd.read_csv('delhi_synthetic_data.csv')

combined = build_final_dataset(real_df, synth_df)
processed, feature_cols, target_col, scaler = encode_and_normalize(combined)
X, y, zone_ids = create_cnn_lstm_sequences(processed, feature_cols, target_col)
export_final_dataset(processed, X, y, feature_cols)
print_paper_summary(processed, X, feature_cols)
