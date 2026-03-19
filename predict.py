"""
SafeHer — Real-Time Safety Score Inference
============================================
After training, use this to predict safety scores for any
Delhi zone at any time — this is what your app calls.

Usage:
    python predict.py
    
Or from your Flask/FastAPI backend:
    from predict import SafeHerPredictor
    predictor = SafeHerPredictor('safeher_cnn_lstm_model.h5')
    score = predictor.predict_zone('Greater Kailash', hour=22, day=5)
"""

import numpy as np
import pandas as pd
import json

class SafeHerPredictor:
    """
    Wraps the trained CNN-LSTM model for real-time inference.
    This class is imported by your FastAPI backend.
    """
    
    def __init__(self, model_path='safeher_cnn_lstm_model.h5',
                       dataset_path='delhi_final_dataset.csv'):
        import tensorflow as tf
        
        print("🔄 Loading SafeHer model...")
        self.model   = tf.keras.models.load_model(model_path)
        self.dataset = pd.read_csv(dataset_path)
        print("✅ Model ready")
    
    def predict_zone(self, zone_name: str, hour: int, day: int) -> dict:
        """
        Predict safety score for a zone at a given time.
        
        Args:
            zone_name : e.g. "Greater Kailash"
            hour      : 0-23
            day       : 0=Monday ... 6=Sunday
        
        Returns:
            dict with safety_score, risk_level, and recommendation
        """
        # Get zone's historical feature profile
        zone_data = self.dataset[self.dataset['zone_name'] == zone_name]
        
        if len(zone_data) == 0:
            return {'error': f'Zone {zone_name} not found'}
        
        # Build a 24-step sequence ending at the requested hour
        # Use zone's actual feature values + vary time features
        features = ['hour_of_day', 'day_of_week', 'is_weekend',
                    'crime_count_normalized', 'police_coverage_score',
                    'street_light_score', 'metro_access_score',
                    'footfall_score', 'sentiment_score']
        
        sequence = []
        base_row = zone_data.iloc[0][features].values.copy()
        
        for step in range(24):
            row = base_row.copy()
            h = (hour - 23 + step) % 24   # 24-hour window ending at requested hour
            row[0] = h / 23.0              # normalized hour
            row[1] = day / 6.0             # normalized day
            row[2] = 1.0 if day >= 5 else 0.0
            sequence.append(row)
        
        X = np.array([sequence])   # shape: (1, 24, 9)
        
        # Predict
        score_norm = float(self.model.predict(X, verbose=0)[0][0])
        score      = round(score_norm * 100, 1)
        
        # Classify risk level (matches your UI legend)
        if score >= 75:
            risk_level     = "Safe"
            color          = "#22c55e"
            recommendation = "Area is considered safe. Stay aware of your surroundings."
        elif score >= 65:
            risk_level     = "Low Risk"
            color          = "#84cc16"
            recommendation = "Generally safe. Avoid isolated areas."
        elif score >= 50:
            risk_level     = "Moderate"
            color          = "#f59e0b"
            recommendation = "Exercise caution. Share your location with a trusted contact."
        elif score >= 35:
            risk_level     = "High Risk"
            color          = "#f97316"
            recommendation = "Avoid if possible. Use SafeHer safe route instead."
        else:
            risk_level     = "Critical"
            color          = "#ef4444"
            recommendation = "Avoid this area. Trigger SOS alert if you must travel here."
        
        return {
            'zone_name'     : zone_name,
            'hour'          : hour,
            'day'           : day,
            'safety_score'  : score,
            'risk_level'    : risk_level,
            'color'         : color,
            'recommendation': recommendation,
        }
    
    def predict_all_zones(self, hour: int, day: int) -> pd.DataFrame:
        """
        Predict safety scores for ALL 70 zones at a given time.
        Used to generate the full heatmap in your UI.
        """
        zones = self.dataset['zone_name'].unique()
        results = []
        
        for zone in zones:
            result = self.predict_zone(zone, hour, day)
            if 'error' not in result:
                results.append({
                    'zone_name'   : zone,
                    'safety_score': result['safety_score'],
                    'risk_level'  : result['risk_level'],
                    'lat'         : self.dataset[self.dataset['zone_name']==zone]['lat'].iloc[0],
                    'lng'         : self.dataset[self.dataset['zone_name']==zone]['lng'].iloc[0],
                })
        
        df = pd.DataFrame(results).sort_values('safety_score', ascending=False)
        return df

# ─── Demo Usage ───────────────────────────────────────────────
if __name__ == "__main__":
    import os
    
    if not os.path.exists('safeher_cnn_lstm_model.h5'):
        print("❌ Model not trained yet. Run train_model.py first.")
        exit(1)
    
    predictor = SafeHerPredictor()
    
    # Test individual zone predictions
    print("\n── Individual Zone Predictions ──")
    test_cases = [
        ("Greater Kailash", 14, 1),   # Tuesday afternoon
        ("Chandni Chowk",   23, 5),   # Saturday midnight
        ("Connaught Place",  9, 0),   # Monday morning
        ("Paharganj",       22, 4),   # Friday night
        ("Dwarka",          18, 2),   # Wednesday evening
    ]
    
    for zone, hour, day in test_cases:
        r = predictor.predict_zone(zone, hour, day)
        days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
        print(f"  {zone:<20} {days[day]} {hour:02d}:00  →  "
              f"Score: {r['safety_score']:5.1f}  [{r['risk_level']}]")
    
    # Generate full heatmap for evening time
    print("\n── Evening Heatmap (Friday 10pm) ──")
    heatmap = predictor.predict_all_zones(hour=22, day=4)
    print("\n  Top 5 Safest:")
    print(heatmap.head(5)[['zone_name','safety_score','risk_level']].to_string(index=False))
    print("\n  Top 5 Most Dangerous:")
    print(heatmap.tail(5)[['zone_name','safety_score','risk_level']].to_string(index=False))
    
    heatmap.to_csv('heatmap_friday_10pm.csv', index=False)
    print("\n✅ Full heatmap saved: heatmap_friday_10pm.csv")
