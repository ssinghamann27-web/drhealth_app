# ============================================
# 📄 server.py — AI Backend for DrHealth App
# ============================================

from __future__ import annotations
import os
import io
import uuid
from typing import Tuple

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

import numpy as np
from PIL import Image
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.preprocessing import image as keras_image

# Optional: LLM via OpenRouter
from openai import OpenAI

# =========================
# 🔧 CONFIGURATION
# =========================
MODEL_PATH = "pneumonia_model.keras"   # trained model file
IMG_SIZE: Tuple[int, int] = (180, 180)
CLASS_NAMES = ["NORMAL", "PNEUMONIA"]

# Folder to save heatmaps
DATA_DIR = os.path.join(os.path.dirname(__file__), "api_data")
os.makedirs(DATA_DIR, exist_ok=True)

# =========================
# 🚀 FLASK APP SETUP
# =========================
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # ✅ Enables access from mobile/web Flutter app

# =========================
# 🧠 LOAD MODEL (Once)
# =========================
print("[INFO] Loading model...")
model = keras.models.load_model(MODEL_PATH)
print("[OK] Model loaded successfully!")

# Warm-up model (build computation graph)
_ = model(tf.zeros((1, *IMG_SIZE, 3)))

# =========================
# 🧩 Preprocess Function
# =========================
def preprocess_image(pil_img: Image.Image) -> np.ndarray:
    img = pil_img.convert("RGB").resize(IMG_SIZE)
    arr = keras_image.img_to_array(img)
    arr = np.expand_dims(arr, axis=0) / 255.0
    return arr

# =========================
# 🔮 Predict Function
# =========================
def predict_np(img_batch: np.ndarray) -> Tuple[str, float, int]:
    preds = model.predict(img_batch, verbose=0)
    pred_idx = int(np.argmax(preds, axis=1)[0])
    conf = float(preds[0][pred_idx])
    label = CLASS_NAMES[pred_idx]
    return label, conf, pred_idx

# =========================
# 🔥 Integrated Gradients
# =========================
def integrated_gradients(
    input_image: tf.Tensor,
    target_class_index: int,
    baseline: tf.Tensor | None = None,
    steps: int = 32,
) -> np.ndarray:
    """Returns attribution heatmap (H, W) via Integrated Gradients"""
    if baseline is None:
        baseline = tf.zeros_like(input_image)

    # Interpolation steps
    interpolated = [
        baseline + (float(i) / steps) * (input_image - baseline)
        for i in range(steps + 1)
    ]
    interpolated = tf.concat(interpolated, axis=0)

    with tf.GradientTape() as tape:
        tape.watch(interpolated)
        preds = model(interpolated, training=False)
        target = preds[:, target_class_index]

    grads = tape.gradient(target, interpolated)
    avg_grads = tf.reduce_mean(grads, axis=0)
    integrated = (input_image[0] - baseline[0]) * avg_grads
    attr = tf.reduce_sum(tf.abs(integrated), axis=-1)

    # Normalize heatmap
    attr = attr - tf.reduce_min(attr)
    attr = attr / (tf.reduce_max(attr) + 1e-8)
    return attr.numpy()

# =========================
# 💬 LLM Explanation (Optional)
# =========================
def llm_explain(label: str, confidence: float) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return (
            f"AI suggests {label} with {confidence:.2%} confidence.\n"
            "A doctor would confirm with physical exam and tests."
        )

    try:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        prompt = (
            "Explain this X-ray diagnosis clearly for a patient.\n"
            f"Prediction: {label}\n"
            f"Confidence: {confidence:.2%}\n"
            "Compare pneumonia vs normal and suggest what doctor might do next."
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"LLM explanation unavailable: {e}"

# =========================
# 📁 Serve Heatmap Files
# =========================
@app.route("/files/<path:filename>", methods=["GET"])
def serve_file(filename: str):
    return send_from_directory(DATA_DIR, filename, as_attachment=False)

# =========================
# 🩺 Health Endpoint
# =========================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

# =========================
# 🧠 Predict Endpoint
# =========================
@app.route("/predict", methods=["POST"])
def predict():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    try:
        pil_img = Image.open(io.BytesIO(file.read()))
    except Exception as e:
        return jsonify({"error": f"Invalid image: {e}"}), 400

    # 🔹 Step 1. Preprocess
    img_batch = preprocess_image(pil_img)

    # 🔹 Step 2. Predict
    label, conf, pred_idx = predict_np(img_batch)

    # 🔹 Step 3. Generate explanation
    explanation = llm_explain(label, conf)

    # 🔹 Step 4. Generate attribution heatmap
    attr = integrated_gradients(tf.convert_to_tensor(img_batch), pred_idx)
    attr_resized = Image.fromarray((attr * 255).astype(np.uint8)).resize(IMG_SIZE)
    attr_gray = np.array(attr_resized.convert("L"))
    heat_rgb = np.zeros((IMG_SIZE[1], IMG_SIZE[0], 3), dtype=np.uint8)
    heat_rgb[..., 0] = attr_gray

    base = pil_img.convert("RGB").resize(IMG_SIZE)
    base_np = np.array(base)
    overlay = (base_np * 0.5 + heat_rgb * 0.5).astype(np.uint8)
    overlay_img = Image.fromarray(overlay)

    # 🔹 Step 5. Save visualization
    out_name = f"viz_{uuid.uuid4().hex}.jpg"
    out_path = os.path.join(DATA_DIR, out_name)
    overlay_img.save(out_path, format="JPEG", quality=92)

    return jsonify({
        "label": label,
        "confidence": round(conf, 4),
        "explanation": explanation,
        "viz_url": f"/files/{out_name}"
    })

# =========================
# ▶️ Run Server
# =========================
if __name__ == "__main__":
    # 🔹 Replace with your LAN IPv4 (same as Flutter _lanIp)
    app.run(host="192.168.29.86", port=8000, debug=False)
