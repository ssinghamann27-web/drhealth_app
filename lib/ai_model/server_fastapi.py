from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import onnxruntime as ort, numpy as np, cv2, io, pickle, pandas as pd

# ==============================================
# DrHealth Phase 5 – Day 4 Integration API
# ==============================================
app = FastAPI(title="DrHealth AI API", version="5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------
# Load Models Once
# ------------------------------
xray_session = ort.InferenceSession("lib/ai_model/models/xray_model.onnx")
with open("lib/ai_model/models/lab_model.pkl","rb") as f:
    lab_model = pickle.load(f)

print("✅ Models loaded successfully.")

# ------------------------------
# Preprocessing Helper
# ------------------------------
def preprocess_image(bytes_data):
    arr = np.frombuffer(bytes_data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    img = cv2.resize(img, (224,224))
    img = img.astype(np.float32) / 255.0
    img = (img - [0.485,0.456,0.406]) / [0.229,0.224,0.225]
    img = np.transpose(img, (2,0,1))[None, ...]  # (1,3,224,224)
    return img

# ------------------------------
# 🩻 X-Ray Prediction Endpoint
# ------------------------------
@app.post("/api/image/predict")
async def predict_image(file: UploadFile = File(...)):
    try:
        img_bytes = await file.read()
        img_np = preprocess_image(img_bytes)
        out = xray_session.run(None, {"input": img_np})[0]
        prob = np.exp(out - np.max(out)); prob = prob / prob.sum()
        label = "PNEUMONIA" if prob[0][1] > prob[0][0] else "NORMAL"
        return {"prediction": label,
                "probabilities": {"NORMAL": float(prob[0][0]),
                                  "PNEUMONIA": float(prob[0][1])}}
    except Exception as e:
        return {"error": str(e)}

# ------------------------------
# 🧪 Lab Analysis Endpoint
# ------------------------------
@app.post("/api/lab/analyze")
async def analyze_lab(glucose: float = Form(...),
                      cholesterol: float = Form(...),
                      hemoglobin: float = Form(...),
                      wbc: float = Form(...)):
    try:
        df = pd.DataFrame([[glucose, cholesterol, hemoglobin, wbc]],
                          columns=["glucose","cholesterol","hemoglobin","wbc"])
        pred = lab_model.predict(df)[0]
        return {"condition": pred}
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
def root():
    return {"status":"DrHealth AI online","xray_model":"ready","lab_model":"ready"}
