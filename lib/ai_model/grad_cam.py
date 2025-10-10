import tensorflow as tf
from tensorflow import keras
import numpy as np
import cv2, os
from tf_explain.core.grad_cam import GradCAM

# =====================================================
# CONFIG
# =====================================================
MODEL_PATH = "pneumonia_model.keras"
IMAGE_PATH = "predict/gradcam_result.jpg"
OUTPUT_PATH = "gradcam_result.jpg"
IMG_SIZE = (180, 180)
CLASS_NAMES = ["NORMAL", "PNEUMONIA"]

# =====================================================
# LOAD MODEL
# =====================================================
print("[INFO] Loading model...")
model = keras.models.load_model(MODEL_PATH)
print("[OK] Model loaded.")

# =====================================================
# LOAD IMAGE
# =====================================================
if not os.path.exists(IMAGE_PATH):
    raise FileNotFoundError(f"❌ File not found: {IMAGE_PATH}")

img = keras.utils.load_img(IMAGE_PATH, target_size=IMG_SIZE)
img_array = keras.utils.img_to_array(img)
img_array = np.expand_dims(img_array, axis=0) / 255.0

# =====================================================
# PREDICT
# =====================================================
preds = model.predict(img_array)
pred_class = int(np.argmax(preds))
pred_conf = float(np.max(preds))
print(f"[RESULT] Predicted: {CLASS_NAMES[pred_class]} ({pred_conf:.2f})")

# =====================================================
# GRAD-CAM via tf-explain
# =====================================================
print("[INFO] Generating Grad-CAM...")
explainer = GradCAM()

# Explain expects data in format: (image, label)
data = ([img_array[0]], None)

# Choose last Conv2D automatically
heatmap = explainer.explain(data, model, class_index=pred_class)

# Save
cv2.imwrite(OUTPUT_PATH, heatmap)
print(f"[✅] Grad-CAM saved at {OUTPUT_PATH}")



