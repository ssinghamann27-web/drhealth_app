import os
import tensorflow as tf
import numpy as np
import pandas as pd
from tensorflow.keras.preprocessing import image

# ✅ Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "pneumonia_model.keras")
PREDICT_DIR = os.path.join(BASE_DIR, "predict")

IMG_SIZE = (180, 180)
CLASSES = ["NORMAL", "PNEUMONIA"]

# ✅ Load trained model
print("[INFO] Loading model...")
model = tf.keras.models.load_model(MODEL_PATH)
print("[OK] Model loaded successfully!\n")

# ✅ Check folder
if not os.path.exists(PREDICT_DIR):
    os.makedirs(PREDICT_DIR)
    print(f"[INFO] Created folder: {PREDICT_DIR}")
    print("[WARN] Drop your images inside the 'predict' folder, then run again.")
    exit()

# ✅ Get files
files = [f for f in os.listdir(PREDICT_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

if not files:
    print("[WARN] No images found in predict/ folder.")
    exit()

print(f"[INFO] Found {len(files)} image(s):\n")

# ✅ Store results
results = []

for file in files:
    path = os.path.join(PREDICT_DIR, file)

    # Load and preprocess
    img = image.load_img(path, target_size=IMG_SIZE)
    img_array = np.expand_dims(image.img_to_array(img) / 255.0, 0)

    # Predict
    pred = model.predict(img_array, verbose=0)
    result = CLASSES[np.argmax(pred)]
    conf = np.max(pred)

    # Log + print
    results.append({"File": file, "Prediction": result, "Confidence": round(float(conf), 2)})
    print(f"{file:<30} -> {result} ({conf:.2f})")

# ✅ Export CSV
csv_path = os.path.join(BASE_DIR, "predict_results.csv")
df = pd.DataFrame(results)
df.to_csv(csv_path, index=False)
print(f"\n✅ Saved results to {csv_path}")

print("\n[OK] Done! All predictions complete.")

