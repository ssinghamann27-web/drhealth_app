from tensorflow import keras
import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt
from tensorflow.keras.preprocessing import image
from openai import OpenAI
import os
import cv2

# ===========================
# CONFIG
# ===========================
MODEL_PATH = "pneumonia_model.keras"
IMG_PATH = "predict/sample.jpg"
IMG_SIZE = (180, 180)
CLASS_NAMES = ["NORMAL", "PNEUMONIA"]

# ===========================
# LOAD MODEL
# ===========================
print("[INFO] Loading model...")
model = keras.models.load_model(MODEL_PATH)
print("[OK] Model loaded successfully!")

# ===========================
# PREPROCESS IMAGE
# ===========================
print("[INFO] Loading and preprocessing image...")
img = image.load_img(IMG_PATH, target_size=IMG_SIZE)
img_array = image.img_to_array(img)
img_array = np.expand_dims(img_array, axis=0) / 255.0
print("[OK] Image loaded & preprocessed.")

# ===========================
# PREDICT
# ===========================
preds = model.predict(img_array)
pred_class = np.argmax(preds)
confidence = preds[0][pred_class]
label = CLASS_NAMES[pred_class]

print(f"\n[RESULT] Predicted: {label} ({confidence:.2f})")

# ===========================
# LLM EXPLANATION (OpenRouter)
# ===========================
print("\n[INFO] Asking LLM to explain...")

api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key:
    print("API key missing. Set it using:")
    print('$env:OPENROUTER_API_KEY="your_api_key"')
    exit()

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

prompt = f"""
Explain this medical image diagnosis:
Prediction: {label}
Confidence: {confidence:.2f}
Condition: Pneumonia vs Normal
Describe what this means in simple medical terms and what next steps a doctor might take.
"""

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=250
    )
    explanation = response.choices[0].message.content
except Exception as e:
    explanation = f"LLM explanation failed: {str(e)}"

print("\n[LLM Explanation]\n")
print(explanation)

# ===========================
# INTEGRATED GRADIENTS (works for Dense models)
# ===========================
print("\n[INFO] Generating Integrated Gradients visualization...")

@tf.function
def interpolate_images(baseline, image, alphas):
    alphas_x = alphas[:, tf.newaxis, tf.newaxis, tf.newaxis]
    delta = image - baseline
    images = baseline + alphas_x * delta
    return images

@tf.function
def compute_gradients(images, model, target_class_idx):
    with tf.GradientTape() as tape:
        tape.watch(images)
        probs = model(images)
        probs = probs[:, target_class_idx]
    grads = tape.gradient(probs, images)
    return grads

def integral_approximation(gradients):
    grads = (gradients[:-1] + gradients[1:]) / 2.0
    integrated_grads = tf.reduce_mean(grads, axis=0)
    return integrated_grads

def integrated_gradients(model, image, baseline=None, target_class_idx=0, m_steps=50):
    if baseline is None:
        baseline = tf.zeros(shape=image.shape)
    alphas = tf.linspace(start=0.0, stop=1.0, num=m_steps+1)
    interpolated_images = interpolate_images(baseline, image, alphas)
    grads = compute_gradients(interpolated_images, model, target_class_idx)
    avg_grads = integral_approximation(grads)
    integrated_grads = (image - baseline) * avg_grads
    return integrated_grads

# Compute IG
ig = integrated_gradients(model, tf.convert_to_tensor(img_array, dtype=tf.float32), target_class_idx=pred_class)
ig = tf.reduce_sum(tf.abs(ig), axis=-1)[0].numpy()
ig = (ig - ig.min()) / (ig.max() - ig.min())

# Convert to heatmap
heatmap = np.uint8(255 * ig)
heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
original = cv2.imread(IMG_PATH)
original = cv2.resize(original, IMG_SIZE)
overlay = cv2.addWeighted(original, 0.6, heatmap, 0.4, 0)

# ✅ Save final result (No emojis)
cv2.imwrite("integrated_gradients_result.jpg", overlay)
print("[OK] Integrated Gradients visualization saved as integrated_gradients_result.jpg")
