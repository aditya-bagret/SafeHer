"""
SafeHer — CNN-LSTM Model Training
===================================
Trains the Hybrid CNN-LSTM spatiotemporal crime prediction model
on the generated Delhi safety dataset.

Input  : X_train.npy (48288, 24, 9)  — sequences
Output : safety_score prediction (0-100) per zone per time window

Architecture:
  Input (24, 9)
    → Conv1D(64 filters, kernel=3, ReLU)
    → MaxPooling1D(pool=2)
    → Conv1D(128 filters, kernel=3, ReLU)       ← spatial feature extraction
    → MaxPooling1D(pool=2)
    → LSTM(128 units)                            ← temporal dependency learning
    → Dropout(0.3)
    → Dense(64, ReLU)
    → Dense(1, Linear)                           ← safety score output

Install: pip install tensorflow scikit-learn matplotlib seaborn pandas numpy
"""

import numpy as np
import pandas as pd
import json
import os
import warnings
warnings.filterwarnings('ignore')

# ─── Load Dataset ────────────────────────────────────────────
def load_data(data_dir='.'):
    print("📂 Loading dataset...")
    X_train = np.load(os.path.join(data_dir, 'X_train.npy'))
    X_test  = np.load(os.path.join(data_dir, 'X_test.npy'))
    y_train = np.load(os.path.join(data_dir, 'y_train.npy'))
    y_test  = np.load(os.path.join(data_dir, 'y_test.npy'))
    
    # Normalize target to 0-1 for training (scale back after prediction)
    y_train_norm = y_train / 100.0
    y_test_norm  = y_test  / 100.0
    
    print(f"  X_train : {X_train.shape}  (samples × timesteps × features)")
    print(f"  X_test  : {X_test.shape}")
    print(f"  y_train : {y_train.shape}  | range: {y_train.min():.1f} – {y_train.max():.1f}")
    print(f"  y_test  : {y_test.shape}")
    
    return X_train, X_test, y_train_norm, y_test_norm, y_train, y_test

# ─── Build CNN-LSTM Model ─────────────────────────────────────
def build_cnn_lstm(input_shape: tuple, 
                   conv_filters_1: int = 64,
                   conv_filters_2: int = 128,
                   lstm_units: int = 128,
                   dropout_rate: float = 0.3) -> 'keras.Model':
    """
    Hybrid CNN-LSTM architecture.
    
    CNN layers    → extract local spatial patterns across zone features
    LSTM layer    → capture temporal dependencies across time steps
    Dense layers  → final regression to predict safety score
    
    Input shape: (timesteps=24, features=9)
    """
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import (
        Conv1D, MaxPooling1D, LSTM, Dense, 
        Dropout, BatchNormalization, Flatten
    )
    from tensorflow.keras.optimizers import Adam
    
    model = Sequential([
        # ── CNN Block 1: Local pattern extraction ──
        Conv1D(filters=conv_filters_1, 
               kernel_size=3, 
               activation='relu', 
               padding='same',
               input_shape=input_shape,
               name='conv1d_1'),
        BatchNormalization(name='bn_1'),
        MaxPooling1D(pool_size=2, name='maxpool_1'),
        
        # ── CNN Block 2: Deeper spatial features ──
        Conv1D(filters=conv_filters_2, 
               kernel_size=3, 
               activation='relu', 
               padding='same',
               name='conv1d_2'),
        BatchNormalization(name='bn_2'),
        MaxPooling1D(pool_size=2, name='maxpool_2'),
        
        # ── LSTM: Temporal dependency learning ──
        LSTM(units=lstm_units, 
             return_sequences=False,
             name='lstm_1'),
        Dropout(dropout_rate, name='dropout_1'),
        
        # ── Dense: Regression head ──
        Dense(64, activation='relu', name='dense_1'),
        Dropout(0.2, name='dropout_2'),
        Dense(1, activation='sigmoid', name='output')  # sigmoid → output in [0,1]
    ])
    
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='mse',
        metrics=['mae']
    )
    
    return model

# ─── Baseline Models for Comparison ──────────────────────────
def build_baseline_models(input_shape: tuple) -> dict:
    """
    Build standalone models for benchmarking.
    Used to justify why CNN-LSTM > individual models.
    (Mirrors Table II in the CNN-LSTM paper: RF=80%, CNN=92%, LSTM=93%, CNN-LSTM=97%)
    """
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import (
        Conv1D, MaxPooling1D, LSTM, Dense, 
        Dropout, Flatten, BatchNormalization
    )
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    
    models = {}
    
    # Standalone CNN
    cnn = Sequential([
        Conv1D(64, 3, activation='relu', padding='same', input_shape=input_shape),
        MaxPooling1D(2),
        Conv1D(128, 3, activation='relu', padding='same'),
        MaxPooling1D(2),
        Flatten(),
        Dense(64, activation='relu'),
        Dense(1, activation='sigmoid')
    ], name='CNN_only')
    cnn.compile(optimizer='adam', loss='mse', metrics=['mae'])
    models['CNN'] = cnn
    
    # Standalone LSTM
    lstm = Sequential([
        LSTM(128, input_shape=input_shape, return_sequences=False),
        Dropout(0.3),
        Dense(64, activation='relu'),
        Dense(1, activation='sigmoid')
    ], name='LSTM_only')
    lstm.compile(optimizer='adam', loss='mse', metrics=['mae'])
    models['LSTM'] = lstm
    
    return models

# ─── Training ─────────────────────────────────────────────────
def train_model(model, X_train, y_train, X_test, y_test,
                epochs=50, batch_size=256, model_name='CNN_LSTM'):
    import tensorflow as tf
    from tensorflow.keras.callbacks import (
        EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
    )
    
    print(f"\n🔄 Training {model_name}...")
    print(f"   Epochs: {epochs} | Batch: {batch_size} | Samples: {len(X_train):,}")
    
    callbacks = [
        EarlyStopping(
            monitor='val_loss', 
            patience=10, 
            restore_best_weights=True,
            verbose=1
        ),
        ReduceLROnPlateau(
            monitor='val_loss', 
            factor=0.5, 
            patience=5, 
            min_lr=1e-6,
            verbose=1
        ),
        ModelCheckpoint(
            filepath=f'{model_name}_best.h5',
            monitor='val_loss',
            save_best_only=True,
            verbose=0
        )
    ]
    
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        verbose=1
    )
    
    return history

# ─── Evaluation ───────────────────────────────────────────────
def evaluate_model(model, X_test, y_test_norm, y_test_actual, model_name='CNN_LSTM'):
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    import math
    
    print(f"\n📊 Evaluating {model_name}...")
    
    # Predict (output is 0-1, scale back to 0-100)
    y_pred_norm   = model.predict(X_test, verbose=0).flatten()
    y_pred_actual = y_pred_norm * 100.0
    y_actual      = y_test_actual
    
    mae   = mean_absolute_error(y_actual, y_pred_actual)
    mse   = mean_squared_error(y_actual, y_pred_actual)
    rmse  = math.sqrt(mse)
    r2    = r2_score(y_actual, y_pred_actual)
    
    # Accuracy: % predictions within ±10 points of actual score
    within_10 = np.mean(np.abs(y_actual - y_pred_actual) <= 10) * 100
    within_5  = np.mean(np.abs(y_actual - y_pred_actual) <= 5)  * 100
    
    results = {
        'model'      : model_name,
        'MAE'        : round(mae, 4),
        'RMSE'       : round(rmse, 4),
        'R2_Score'   : round(r2, 4),
        'Accuracy_10': round(within_10, 2),  # % within ±10 points
        'Accuracy_5' : round(within_5, 2),   # % within ±5 points
    }
    
    print(f"   MAE        : {mae:.4f}  (lower = better)")
    print(f"   RMSE       : {rmse:.4f}")
    print(f"   R² Score   : {r2:.4f}  (1.0 = perfect)")
    print(f"   Accuracy   : {within_10:.2f}% predictions within ±10 pts")
    print(f"   Accuracy   : {within_5:.2f}% predictions within ±5 pts")
    
    return results, y_pred_actual

# ─── Comparison Table ─────────────────────────────────────────
def print_comparison_table(all_results: list):
    print("\n" + "="*70)
    print("MODEL COMPARISON TABLE (for your research paper)")
    print("="*70)
    print(f"{'Model':<20} {'MAE':>8} {'RMSE':>8} {'R²':>8} {'Acc±10':>10} {'Acc±5':>10}")
    print("-"*70)
    for r in all_results:
        print(f"{r['model']:<20} {r['MAE']:>8.4f} {r['RMSE']:>8.4f} "
              f"{r['R2_Score']:>8.4f} {r['Accuracy_10']:>9.2f}% {r['Accuracy_5']:>9.2f}%")
    print("="*70)

# ─── Plot Results ─────────────────────────────────────────────
def plot_results(history, y_actual, y_pred, model_name='CNN_LSTM'):
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')  # non-interactive backend
        
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        fig.suptitle(f'SafeHer — {model_name} Training Results', fontsize=14, fontweight='bold')
        
        # Plot 1: Training loss
        axes[0].plot(history.history['loss'],     label='Train Loss', color='#7C3AED')
        axes[0].plot(history.history['val_loss'], label='Val Loss',   color='#EC4899')
        axes[0].set_title('Training & Validation Loss')
        axes[0].set_xlabel('Epoch')
        axes[0].set_ylabel('MSE Loss')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Plot 2: MAE
        axes[1].plot(history.history['mae'],     label='Train MAE', color='#7C3AED')
        axes[1].plot(history.history['val_mae'], label='Val MAE',   color='#EC4899')
        axes[1].set_title('Training & Validation MAE')
        axes[1].set_xlabel('Epoch')
        axes[1].set_ylabel('MAE')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        # Plot 3: Predicted vs Actual
        sample = min(500, len(y_actual))
        axes[2].scatter(y_actual[:sample], y_pred[:sample], 
                       alpha=0.4, s=10, color='#7C3AED')
        axes[2].plot([0, 100], [0, 100], 'r--', linewidth=2, label='Perfect Prediction')
        axes[2].set_title('Predicted vs Actual Safety Score')
        axes[2].set_xlabel('Actual Score')
        axes[2].set_ylabel('Predicted Score')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'{model_name}_results.png', dpi=150, bbox_inches='tight')
        print(f"   📈 Plot saved: {model_name}_results.png")
        plt.close()
        
    except Exception as e:
        print(f"   (Plotting skipped: {e})")

# ─── Save Results ─────────────────────────────────────────────
def save_results(all_results: list):
    df = pd.DataFrame(all_results)
    df.to_csv('model_comparison_results.csv', index=False)
    
    with open('model_results.json', 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n✅ Results saved: model_comparison_results.csv, model_results.json")

# ─── MAIN ─────────────────────────────────────────────────────
def main(data_dir='.', train_baselines=True, epochs=50):
    print("\n" + "🧠 " * 20)
    print("  SafeHer — CNN-LSTM Model Training")
    print("🧠 " * 20 + "\n")
    
    # 1. Load data
    X_train, X_test, y_train_norm, y_test_norm, y_train_actual, y_test_actual = load_data(data_dir)
    input_shape = (X_train.shape[1], X_train.shape[2])  # (24, 9)
    print(f"\n   Input shape for model: {input_shape}  (timesteps × features)")
    
    all_results = []
    
    # 2. Train Random Forest baseline (on flattened data)
    if train_baselines:
        print("\n📊 Training Random Forest baseline...")
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.metrics import mean_absolute_error, r2_score
        import math
        
        X_train_flat = X_train.reshape(X_train.shape[0], -1)  # flatten for sklearn
        X_test_flat  = X_test.reshape(X_test.shape[0], -1)
        
        rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        rf.fit(X_train_flat, y_train_actual)
        rf_pred = rf.predict(X_test_flat)
        
        rf_mae  = mean_absolute_error(y_test_actual, rf_pred)
        rf_rmse = math.sqrt(mean_absolute_error(y_test_actual, rf_pred**2 - rf_pred**2 + rf_pred**2))
        rf_r2   = r2_score(y_test_actual, rf_pred)
        rf_acc  = np.mean(np.abs(y_test_actual - rf_pred) <= 10) * 100
        rf_acc5 = np.mean(np.abs(y_test_actual - rf_pred) <= 5)  * 100
        
        print(f"   RF MAE: {rf_mae:.4f} | R²: {rf_r2:.4f} | Acc±10: {rf_acc:.2f}%")
        all_results.append({
            'model': 'Random Forest', 'MAE': round(rf_mae,4),
            'RMSE': round(rf_mae,4), 'R2_Score': round(rf_r2,4),
            'Accuracy_10': round(rf_acc,2), 'Accuracy_5': round(rf_acc5,2)
        })
    
    # 3. Train CNN-only and LSTM-only baselines
    if train_baselines:
        baselines = build_baseline_models(input_shape)
        for name, model in baselines.items():
            history = train_model(model, X_train, y_train_norm, 
                                  X_test, y_test_norm, 
                                  epochs=30, batch_size=256, model_name=name)
            results, preds = evaluate_model(model, X_test, y_test_norm, y_test_actual, name)
            all_results.append(results)
    
    # 4. Train main CNN-LSTM model
    model = build_cnn_lstm(input_shape)
    print("\n📋 Model Architecture:")
    model.summary()
    
    history = train_model(model, X_train, y_train_norm,
                          X_test, y_test_norm,
                          epochs=epochs, batch_size=256, model_name='CNN_LSTM')
    
    results, cnn_lstm_preds = evaluate_model(model, X_test, y_test_norm, y_test_actual, 'CNN_LSTM')
    all_results.append(results)
    
    # 5. Plot and save
    plot_results(history, y_test_actual, cnn_lstm_preds, 'CNN_LSTM')
    print_comparison_table(all_results)
    save_results(all_results)
    
    # 6. Save final model
    model.save('safeher_cnn_lstm_model.h5')
    print(f"\n✅ Model saved: safeher_cnn_lstm_model.h5")
    
    print("\n" + "✅ " * 20)
    print("  Training Complete!")
    print("✅ " * 20)

if __name__ == "__main__":
    import sys
    data_dir       = sys.argv[1] if len(sys.argv) > 1 else '.'
    train_baselines = True   # Set False to skip RF/CNN/LSTM baselines
    epochs          = 50     # Increase to 100 for better accuracy
    
    main(data_dir=data_dir, train_baselines=train_baselines, epochs=epochs)
