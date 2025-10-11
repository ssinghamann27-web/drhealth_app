import pandas as pd, numpy as np, os, pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# ==============================================
# DrHealth Phase 5 – Lab Data Training Script
# ==============================================

MODEL_SAVE_PATH = 'lib/ai_model/models/lab_model.pkl'
DATA_PATH = 'ml/data/lab_synthetic.csv'
os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)

# ------------------------------
# 1. Create synthetic lab dataset
# ------------------------------
np.random.seed(42)
rows = 2000
data = {
    'glucose': np.random.normal(100, 30, rows),
    'cholesterol': np.random.normal(180, 40, rows),
    'hemoglobin': np.random.normal(13.5, 2.5, rows),
    'wbc': np.random.normal(7000, 1500, rows),
}
df = pd.DataFrame(data)

def classify(r):
    risk = 0
    if r['glucose'] > 140 or r['cholesterol'] > 240: risk += 1
    if r['hemoglobin'] < 11: risk += 1
    if r['wbc'] > 11000: risk += 1
    if risk == 0: return 'Normal'
    elif risk == 1: return 'Mild Risk'
    else: return 'High Risk'

df['condition'] = df.apply(classify, axis=1)
df.to_csv(DATA_PATH, index=False)
print(f'✅ Synthetic lab dataset saved → {DATA_PATH}')

# ------------------------------
# 2. Split & train
# ------------------------------
X = df[['glucose','cholesterol','hemoglobin','wbc']]
y = df['condition']
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
model = RandomForestClassifier(n_estimators=120, random_state=42)
model.fit(X_train, y_train)

# ------------------------------
# 3. Evaluate
# ------------------------------
pred = model.predict(X_val)
print('Accuracy:', round(accuracy_score(y_val, pred)*100, 2), '%')
print(classification_report(y_val, pred))

# ------------------------------
# 4. Export model
# ------------------------------
os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)
with open(MODEL_SAVE_PATH, 'wb') as f:
    pickle.dump(model, f)
print(f'💾 Model exported → {MODEL_SAVE_PATH}')
