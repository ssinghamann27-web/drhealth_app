from tensorflow import keras
import numpy as np
from tensorflow.keras.preprocessing import image

MODEL_PATH = "pneumonia_model.keras"
IMG_PATH = "predict/sample.jpg"
IMG_SIZE = (180, 180)
CLASS_NAMES = ["NORMAL", "PNEUMONIA"]

print("[INFO] Loading model...")
model = keras.models.load_model(MODEL_PATH)
print("[OK] Model loaded!")

# Load and preprocess image
img = image.load_img(IMG_PATH, target_size=IMG_SIZE)
img_array = image.img_to_array(img)
img_array = np.expand_dims(img_array, axis=0) / 255.0

# Predict
preds = model.predict(img_array)
pred_class = np.argmax(preds)
confidence = preds[0][pred_class]

print(f"[RESULT] Predicted: {CLASS_NAMES[pred_class]} ({confidence:.2f})")
