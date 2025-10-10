# server_multitask.py
from __future__ import annotations
import os, io, uuid, re, json, traceback
from typing import Tuple, Dict, Any

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# --- Load .env (optional) ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# --- Core ML / Image ---
import numpy as np
from PIL import Image, UnidentifiedImageError
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.preprocessing import image as keras_image

# --- OCR, PDF, DICOM ---
import pytesseract
import pdfplumber
import pydicom
from pydicom.pixel_data_handlers.util import apply_voi_lut

# --- LLM via OpenRouter (optional) ---
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, "pneumonia_model.keras")
IMG_SIZE: Tuple[int, int] = (180, 180)
CLASS_NAMES = ["NORMAL", "PNEUMONIA"]

# Output dir
DATA_DIR = os.path.join(BASE_DIR, "api_data")
os.makedirs(DATA_DIR, exist_ok=True)

# Request size guard (e.g., 32MB)
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH_BYTES", "33554432"))  # 32 * 1024 * 1024

# Tesseract path (Windows)
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "").strip()
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# LLM usage toggle
USE_LLM = os.getenv("USE_LLM", "1").strip() not in ("0", "false", "False", "")

# =========================
# APP
# =========================
app = Flask(__name__, static_folder=None)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# =========================
# LOAD MODEL
# =========================
MODEL_READY = False
try:
    print("[INFO] Loading model...")
    model = keras.models.load_model(MODEL_PATH)
    # warmup
    _ = model(tf.zeros((1, *IMG_SIZE, 3)))
    MODEL_READY = True
    print("[OK] Model loaded.")
except Exception as e:
    model = None
    print(f"[ERR] Failed to load model: {e}")

# =========================
# UTILS
# =========================
def preprocess_image(pil_img: Image.Image) -> np.ndarray:
    img = pil_img.convert("RGB").resize(IMG_SIZE)
    arr = keras_image.img_to_array(img)
    arr = np.expand_dims(arr, axis=0) / 255.0
    return arr

def predict_np(img_batch: np.ndarray) -> Tuple[str, float, int, np.ndarray]:
    if model is None:
        raise RuntimeError("Model not loaded")
    preds = model.predict(img_batch, verbose=0)
    idx = int(np.argmax(preds, axis=1)[0])
    conf = float(preds[0][idx])
    return CLASS_NAMES[idx], conf, idx, preds[0]

def integrated_gradients(img: tf.Tensor, idx: int, steps=32) -> np.ndarray:
    baseline = tf.zeros_like(img)
    scaled = [baseline + (i / steps) * (img - baseline) for i in range(steps + 1)]
    stacked = tf.concat(scaled, axis=0)
    with tf.GradientTape() as tape:
        tape.watch(stacked)
        preds = model(stacked)
        target = preds[:, idx]
    grads = tape.gradient(target, stacked)
    avg_grads = tf.reduce_mean(grads, axis=0)
    integrated = (img[0] - baseline[0]) * avg_grads
    attr = tf.reduce_sum(tf.abs(integrated), axis=-1)
    attr = (attr - tf.reduce_min(attr)) / (tf.reduce_max(attr) + 1e-8)
    return attr.numpy()

def save_heatmap_overlay(img: Image.Image, attr: np.ndarray) -> str:
    attr_img = Image.fromarray((attr * 255).astype(np.uint8)).resize(IMG_SIZE)
    heat = np.array(attr_img.convert("L"))
    rgb = np.zeros((IMG_SIZE[1], IMG_SIZE[0], 3), np.uint8)
    rgb[..., 0] = heat
    base = np.array(img.convert("RGB").resize(IMG_SIZE))
    overlay = (base * 0.5 + rgb * 0.5).astype(np.uint8)
    out = Image.fromarray(overlay)
    name = f"viz_{uuid.uuid4().hex}.jpg"
    path = os.path.join(DATA_DIR, name)
    out.save(path, "JPEG", quality=90)
    return f"/files/{name}"

def llm_summary(prompt: str, tokens=400) -> str:
    if not USE_LLM:
        return "LLM disabled by server configuration."
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key or OpenAI is None:
        return "LLM unavailable (no API key)."
    try:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=tokens,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"LLM error: {e}"

# --- OCR + PDF ---
def pdf_to_text(pdf_bytes: bytes) -> str:
    out = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for p in pdf.pages:
            try:
                txt = p.extract_text() or ""
            except Exception:
                txt = ""
            if txt.strip():
                out.append(txt)
    return "\n".join(out)

def image_to_text(data: bytes) -> str:
    try:
        img = Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(img)
    except Exception:
        return ""

# --- DICOM helpers ---
def dicom_to_pil(data: bytes) -> Image.Image:
    ds = pydicom.dcmread(io.BytesIO(data), force=True)
    if "PixelData" not in ds:
        raise ValueError("DICOM has no PixelData")
    arr = ds.pixel_array

    try:
        arr = apply_voi_lut(arr, ds)
    except Exception:
        pass

    # Invert MONOCHROME1 (white=low values)
    try:
        if getattr(ds, "PhotometricInterpretation", "").upper() == "MONOCHROME1":
            arr = np.max(arr) - arr
    except Exception:
        pass

    arr = arr.astype(np.float32)
    vmin, vmax = float(np.min(arr)), float(np.max(arr))
    if vmax <= vmin:
        raise ValueError("Invalid DICOM pixel range")
    arr = (arr - vmin) / (vmax - vmin)
    arr_u8 = (arr * 255).astype(np.uint8)

    if arr_u8.ndim == 2:
        img = Image.fromarray(arr_u8, "L").convert("RGB")
    else:
        img = Image.fromarray(arr_u8).convert("RGB")
    return img

# --- Lab Value Extraction ---
def extract_labs(text: str) -> Dict[str, Any]:
    patterns = {
        "Hemoglobin": r"hemoglobin[^0-9]*([0-9.]+)",
        "WBC": r"\bwbc\b[^0-9]*([0-9.]+)",
        "Platelets": r"platelets?[^0-9]*([0-9.]+)",
        "Glucose": r"glucose[^0-9]*([0-9.]+)",
        "Creatinine": r"creatinine[^0-9]*([0-9.]+)",
        "Sodium": r"sodium[^0-9]*([0-9.]+)",
        "Potassium": r"potassium[^0-9]*([0-9.]+)",
    }
    ranges = {
        "Hemoglobin": (12, 17.5),
        "WBC": (4, 11),
        "Platelets": (150, 450),
        "Glucose": (70, 99),
        "Creatinine": (0.6, 1.3),
        "Sodium": (135, 145),
        "Potassium": (3.5, 5.1),
    }
    out = {}
    for k, p in patterns.items():
        m = re.search(p, text, re.I)
        if not m:
            continue
        try:
            val = float(m.group(1))
        except Exception:
            val = m.group(1)
        flag = "unknown"
        if isinstance(val, float) and k in ranges:
            lo, hi = ranges[k]
            if val < lo:
                flag = "low"
            elif val > hi:
                flag = "high"
            else:
                flag = "normal"
        out[k] = {"value": val, "flag": flag}
    return out

# =========================
# ROUTES
# =========================
@app.get("/files/<path:filename>")
def serve_file(filename):
    return send_from_directory(DATA_DIR, filename, as_attachment=False)

@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "model_ready": MODEL_READY,
        "img_size": IMG_SIZE,
        "class_names": CLASS_NAMES
    })

# --- XRAY ---
@app.post("/predict/xray")
def predict_xray():
    try:
        f = request.files.get("file")
        if not f or not f.filename:
            return jsonify({"error": "no file"}), 400
        data = f.read()
        if not data:
            return jsonify({"error": "empty file"}), 400

        try:
            img = Image.open(io.BytesIO(data))
        except UnidentifiedImageError:
            return jsonify({"error": "unsupported image format"}), 400

        batch = preprocess_image(img)
        label, conf, idx, raw = predict_np(batch)
        attr = integrated_gradients(tf.convert_to_tensor(batch), idx)
        viz = save_heatmap_overlay(img, attr)
        findings = {CLASS_NAMES[i]: float(raw[i]) for i in range(len(raw))}
        prompt = f"You are a radiologist. Predicted {label} ({conf:.2f}). Explain findings: {findings}"
        summary = llm_summary(prompt)
        return jsonify({
            "label": label,
            "confidence": round(conf, 4),
            "findings": findings,
            "viz_url": viz,
            "summary": summary
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"server error: {str(e)}"}), 500

@app.post("/predict")
def predict_alias():
    return predict_xray()

# --- DICOM (hardened) ---
@app.post("/predict/dicom")
def predict_dicom():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file part named 'file' in form-data"}), 400
        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "Filename is empty"}), 400

        data = file.read()
        if not data:
            return jsonify({"error": "Uploaded file is empty"}), 400

        try:
            image_rgb = dicom_to_pil(data)
        except Exception as e:
            return jsonify({"error": f"Failed to read DICOM: {e}"}), 400

        img_batch = preprocess_image(image_rgb)
        label, conf, pred_idx, raw = predict_np(img_batch)
        attr = integrated_gradients(tf.convert_to_tensor(img_batch), pred_idx)
        viz_url = save_heatmap_overlay(image_rgb, attr)

        findings = {CLASS_NAMES[i]: float(raw[i]) for i in range(len(raw))}
        prompt = (
            f"You are a radiologist. Analyze this DICOM scan. "
            f"Prediction: {label} ({conf:.2f}). Findings: {findings}"
        )
        explanation = llm_summary(prompt, 400)

        return jsonify({
            "label": label,
            "confidence": round(conf, 4),
            "findings": findings,
            "viz_url": viz_url,
            "summary": explanation
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"server error: {str(e)}"}), 500

# --- LAB ---
@app.post("/predict/lab")
def predict_lab():
    try:
        f = request.files.get("file")
        if not f:
            return jsonify({"error": "no file"}), 400
        name = f.filename.lower()
        data = f.read()
        if not data:
            return jsonify({"error": "empty file"}), 400

        if name.endswith(".pdf"):
            text = pdf_to_text(data)
        elif name.endswith(".txt"):
            text = data.decode("utf-8", errors="ignore")
        else:
            text = image_to_text(data)

        values = extract_labs(text)
        prompt = f"You are a clinician. Explain this lab report: {json.dumps(values, indent=2)}"
        summary = llm_summary(prompt)
        return jsonify({
            "values": values,
            "raw_excerpt": text[:1500],
            "summary": summary
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"server error: {str(e)}"}), 500

# --- TEXT ---
@app.post("/predict/text")
def predict_text():
    try:
        body = request.form.get("text") or (request.json or {}).get("text", "")
        if not body or not str(body).strip():
            return jsonify({"error": "Provide 'text'"}), 400
        prompt = f"Summarize this clinical note: {body}"
        return jsonify({"summary": llm_summary(prompt, 450)})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"server error: {str(e)}"}), 500

# =========================
if __name__ == "__main__":
    app.run(host="192.168.29.86", port=8000, debug=False)




