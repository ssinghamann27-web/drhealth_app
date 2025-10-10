from __future__ import annotations
import os, io, re, time, base64, logging, psutil, uuid, secrets, json
from typing import Dict, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta

import numpy as np
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form, Depends
from fastapi.responses import JSONResponse, HTMLResponse, PlainTextResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
import pytesseract, pdfplumber, pydicom
from pydicom.pixel_data_handlers.util import apply_voi_lut
import onnxruntime as ort
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fpdf import FPDF

# ---------- Optional deps ----------
try:
    import openai
except Exception:
    openai = None

try:
    import speech_recognition as sr
except Exception:
    sr = None

# =====================================================
# CONFIG
# =====================================================
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "api_data")
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Phase 2 branding
APP_TITLE = "drhealth — Phase 2 • AI Doctor Toolkit (Hybrid)"

# App/AI config
ONNX_PATH = os.getenv("ONNX_MODEL_PATH", os.path.join(BASE_DIR, "pneumonia_model.onnx"))
IMG_SIZE = (180, 180)
CLASS_NAMES = ["NORMAL", "PNEUMONIA"]

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey123")  # change in prod
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "changeme-super-secret")  # header: X-Admin-Token

# Rate limiting
RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "180"))

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if OPENAI_API_KEY and openai:
    try:
        openai.api_key = OPENAI_API_KEY
    except Exception:
        pass

SUPPORTED_LANGS = [
    ("en", "English"), ("es", "Español"), ("fr", "Français"),
    ("hi", "हिन्दी"), ("ar", "العربية"), ("pt", "Português")
]

# =====================================================
# APP INIT
# =====================================================
app = FastAPI(title=APP_TITLE, docs_url="/docs", redoc_url="/redoc")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

# =====================================================
# LOGGING (for Promtail + JSONL audit)
# =====================================================
APP_LOG_FILE = "/app/logs/app.log"  # Promtail will read this inside the container
os.makedirs(os.path.dirname(APP_LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),  # console logs
        logging.FileHandler(os.path.join(LOG_DIR, "api_access.jsonl"), encoding="utf-8"),  # JSON lines
        logging.FileHandler(APP_LOG_FILE, encoding="utf-8"),  # Loki-readable plain text
    ],
)

logger = logging.getLogger("drhealth")

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 DrHealth FastAPI started successfully")

# =====================================================
# PROMETHEUS METRICS
# =====================================================
REQ_COUNT = Counter("api_requests_total", "Total API requests", ["endpoint", "method", "status"])
REQ_LATENCY = Histogram("api_request_latency_seconds", "Latency", ["endpoint"])
INPROGRESS = Gauge("api_inprogress", "Requests in progress")
# ---------- LLM METRICS ----------
LLM_TOKENS_TOTAL = Counter("llm_tokens_total", "Total tokens processed by LLM")
LLM_REQUESTS_TOTAL = Counter("llm_requests_total", "Total LLM API requests")
LLM_LATENCY = Histogram("llm_response_latency_seconds", "LLM response latency in seconds")

_ip_buckets: Dict[str, deque[float]] = defaultdict(lambda: deque())
_user_buckets: Dict[int, deque[float]] = defaultdict(lambda: deque())

def _allow_bucket(bucket: deque, now: float) -> bool:
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT_RPM:
        return False
    bucket.append(now)
    return True

def allow_ip(ip: str, now: float) -> bool:
    return _allow_bucket(_ip_buckets[ip], now)

def allow_user_bucket(uid: int, now: float) -> bool:
    return _allow_bucket(_user_buckets[uid], now)

# =====================================================
# DATABASE (SQLite + SQLAlchemy)
# =====================================================
DB_PATH = os.path.join(BASE_DIR, "drhealth.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(20), default="user")
    created_at = Column(DateTime, default=datetime.utcnow)
    chats = relationship("ChatMessage", back_populates="user")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String(20))  # "user" | "assistant"
    text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="chats")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =====================================================
# AUTH (JWT)
# =====================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def hash_password(p: str) -> str:
    return pwd_context.hash(p)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(401, "Invalid token")
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user

def require_admin_header(req: Request):
    if req.headers.get("X-Admin-Token") != ADMIN_TOKEN:
        raise HTTPException(403, "Forbidden")

# =====================================================
# MEMORY FOR PUBLIC SESSIONS (Demo UI)
# =====================================================
SESSIONS: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10))
USER_ANALYTICS = defaultdict(lambda: {"messages": 0, "visits": 0, "created": datetime.utcnow().isoformat()})

def _get_sid(request: Request) -> str:
    return request.cookies.get("sid", "")

def _ensure_sid_cookie(request: Request, response):
    if "sid" not in request.cookies:
        sid = secrets.token_hex(16)
        response.set_cookie("sid", sid, httponly=True, samesite="lax", max_age=60*60*24*7)
        return sid
    return request.cookies["sid"]

# =====================================================
# MODEL LOAD
# =====================================================
try:
    session_onnx = ort.InferenceSession(ONNX_PATH, providers=["CPUExecutionProvider"])
    IN_NAME = session_onnx.get_inputs()[0].name
    OUT_NAME = session_onnx.get_outputs()[0].name
    IN_SHAPE = session_onnx.get_inputs()[0].shape
    IO_LAYOUT = "NHWC" if (len(IN_SHAPE) == 4 and IN_SHAPE[-1] == 3) else "NCHW"
except Exception as e:
    logger.warning(f"ONNX model not loaded: {e}")
    session_onnx = None
    IN_NAME = OUT_NAME = IO_LAYOUT = None

# =====================================================
# Helper: translate + local doctor persona + LLM
# =====================================================
def translate_text(txt: str, lang: str) -> str:
    lang = (lang or "en").lower()
    fallback = {
        "hi": "यदि लक्षण बने रहें तो डॉक्टर से परामर्श करें। हाइड्रेटेड रहें और आराम करें।",
        "es": "Consulte a un médico si los síntomas persisten. Manténgase hidratado y descanse.",
        "fr": "Consultez un médecin si les symptômes persistent. Restez hydraté et reposez-vous.",
        "pt": "Consulte um médico se os sintomas persistirem. Mantenha-se hidratado e descanse."
    }
    return txt if lang == "en" else fallback.get(lang, txt)

def local_doctor_response(prompt: str) -> str:
    q = (prompt or "").lower()
    response = "I'm your AI Doctor. Based on your description:\n"
    if "fever" in q:
        response += " You may have an infection. Monitor your temperature and stay hydrated."
    elif "cough" in q:
        response += " Could be common cold or allergy. Drink warm fluids and avoid cold air."
    elif "chest pain" in q:
        response += " Possible muscle strain or cardiac issue. Seek emergency care if severe."
    elif "headache" in q:
        response += " Possibly due to stress, dehydration, or eye strain. Rest and hydrate."
    else:
        response += " Please describe your symptoms in more detail."
    return response + "\nIf symptoms persist, consult a clinician."

def differential_diagnosis(question: str):
    q = (question or "").lower()
    conditions = []
    if "fever" in q: conditions += ["Viral Fever", "Typhoid", "COVID-19"]
    if "cough" in q: conditions += ["Bronchitis", "Common Cold", "Asthma"]
    if "chest pain" in q: conditions += ["Muscle Strain", "Angina", "Pneumonia"]
    if "headache" in q: conditions += ["Migraine", "Stress", "Dehydration"]
    if not conditions: conditions.append("General Fatigue or Stress")
    return conditions

def llm_reply(prompt: str) -> str:
    """Try OpenAI; fallback to local rule-based."""
    if OPENAI_API_KEY and openai:
        try:
            chat = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an AI Doctor. Be concise, cautious, and general."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=300
            )
            return (chat.choices[0].message.content or "").strip()
        except Exception as e:
            logger.warning(f"OpenAI failed: {e}")
    return local_doctor_response(prompt)

# =====================================================
# MIDDLEWARE (Metrics + Session cookie for public UI)
# =====================================================
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    INPROGRESS.inc()
    response = None
    try:
        if not allow_ip(request.client.host, start):
            return JSONResponse(status_code=429, content={"detail": "Too many requests"})
        response = await call_next(request)
        status = getattr(response, "status_code", 500)
        _ensure_sid_cookie(request, response)
        sid = _get_sid(request)
        if sid:
            USER_ANALYTICS[sid]["visits"] += 1
        return response
    except Exception as e:
        logger.exception(f"Unhandled: {e}")
        response = JSONResponse(status_code=500, content={"detail": "Server error"})
        _ensure_sid_cookie(request, response)
        return response
    finally:
        INPROGRESS.dec()
        REQ_COUNT.labels(request.url.path, request.method, str(status if response else 500)).inc()
        REQ_LATENCY.labels(request.url.path).observe(time.time() - start)

# =====================================================
# AUTH ROUTES (JWT + DB)
# =====================================================
@app.post("/auth/register")
def register_user(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "Email already registered")
    user = User(email=email, password_hash=hash_password(password))
    db.add(user); db.commit()
    return {"ok": True, "message": "User registered successfully"}

@app.post("/auth/login")
def login_user(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer", "role": user.role}

# =====================================================
# ADMIN / METRICS (HEADER TOKEN)
# =====================================================
@app.get("/admin/config")
async def admin_config(req: Request):
    require_admin_header(req)
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "rate_limit_rpm": RATE_LIMIT_RPM,
        "onnx_model_path": ONNX_PATH,
        "class_names": CLASS_NAMES,
        "admin_token_hint": "Send via X-Admin-Token header",
        "active_sessions": len(SESSIONS),
        "tracked_users": len(USER_ANALYTICS),
    }

@app.get("/admin/metrics/raw")
async def admin_metrics_raw(req: Request):
    require_admin_header(req)
    total_requests = sum(int(s.value) for m in REQ_COUNT.collect() for s in m.samples)
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    try:
        in_prog = float(INPROGRESS._value.get())  # best-effort
    except Exception:
        in_prog = 0.0
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "cpu_percent": cpu,
        "mem_percent": mem,
        "requests_total": total_requests,
        "rate_limit_rpm": RATE_LIMIT_RPM,
        "in_progress": in_prog,
    }

@app.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    return PlainTextResponse(generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST)

# =====================================================
# CORE AI ROUTES
# =====================================================
@app.post("/api/image/predict")
async def predict_image(file: UploadFile = File(...), request: Request = None):
    ip = request.client.host if request and request.client else "unknown"
    if not allow_ip(ip, time.time()):
        raise HTTPException(429, "Rate limit exceeded")
    if session_onnx is None:
        raise HTTPException(500, "Model not loaded")
    img = Image.open(io.BytesIO(await file.read())).convert("RGB").resize(IMG_SIZE)
    arr = np.array(img) / 255.0
    if IO_LAYOUT == "NCHW":
        arr = np.transpose(arr, (2, 0, 1))
    arr = np.expand_dims(arr, 0).astype(np.float32)
    preds = session_onnx.run([OUT_NAME], {IN_NAME: arr})[0][0]
    i = int(np.argmax(preds))
    return {"prediction": CLASS_NAMES[i], "confidence": float(np.max(preds))}

@app.post("/api/ocr/extract")
async def ocr_extract(file: UploadFile = File(...)):
    ext = (file.filename or "").lower().split(".")[-1]
    if ext in {"jpg", "jpeg", "png"}:
        text = pytesseract.image_to_string(Image.open(io.BytesIO(await file.read())))
    elif ext == "pdf":
        pdf = pdfplumber.open(io.BytesIO(await file.read()))
        text = "\n".join([p.extract_text() or "" for p in pdf.pages])
    else:
        raise HTTPException(400, "Unsupported file format")
    return {"text": text.strip()}

@app.post("/api/dicom/analyze")
async def dicom_analyze(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".dcm"):
        raise HTTPException(400, "Not a DICOM file")
    data = pydicom.dcmread(io.BytesIO(await file.read()))
    meta = {e.name: str(e.value)[:120] for e in data}
    img_b64 = None
    if hasattr(data, "pixel_array"):
        px = apply_voi_lut(data.pixel_array, data)
        px = (px - np.min(px)) / max(np.ptp(px), 1) * 255
        px = px.astype(np.uint8)
        buf = io.BytesIO()
        Image.fromarray(px).save(buf, "PNG")
        img_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    return {"metadata": meta, "preview": img_b64}

@app.post("/api/lab/analyze")
async def lab_analyze(file: UploadFile = File(...)):
    ext = (file.filename or "").lower().split(".")[-1]
    if ext in {"jpg", "jpeg", "png"}:
        text = pytesseract.image_to_string(Image.open(io.BytesIO(await file.read())))
    elif ext == "pdf":
        pdf = pdfplumber.open(io.BytesIO(await file.read()))
        text = "\n".join([p.extract_text() or "" for p in pdf.pages])
    else:
        raise HTTPException(400, "Unsupported file format")

    findings, summary = [], []
    def ex(patt, name):
        m = re.search(patt, text.lower())
        if m: findings.append(f"{name}: {m.group(1)}")

    ex(r"hemoglobin[:\s]*([0-9.]+)", "Hemoglobin")
    ex(r"glucose[:\s]*([0-9.]+)", "Glucose")

    for f in findings:
        if "hemoglobin" in f.lower():
            try:
                val = float(re.findall(r"[0-9.]+", f)[0])
                if val < 12: summary.append("Low Hemoglobin")
            except Exception:
                pass

    if not summary:
        summary.append("Normal")
    return {"findings": findings, "summary": summary}

@app.post("/api/translate")
async def translate(text: str = Form(...), target_lang: str = Form("en")):
    return {"translated": translate_text(text, target_lang)}

@app.post("/api/voice/transcribe")
async def voice_transcribe(file: UploadFile = File(...)):
    if sr is None:
        raise HTTPException(500, "speech_recognition not installed. Run: pip install SpeechRecognition pydub")
    ext = (file.filename or "").lower().split(".")[-1]
    if ext not in {"wav", "mp3"}:
        raise HTTPException(400, "Upload .wav or .mp3 only")

    temp = os.path.join(DATA_DIR, f"{uuid.uuid4()}.{ext}")
    with open(temp, "wb") as f:
        f.write(await file.read())

    recog = sr.Recognizer()
    try:
        with sr.AudioFile(temp) as src:
            audio = recog.record(src)
            text = recog.recognize_google(audio)
    except Exception as e:
        os.remove(temp)
        raise HTTPException(500, f"Speech recognition failed: {str(e)}")
    os.remove(temp)
    return {"text": text}

@app.post("/api/export/pdf")
async def export_pdf(title: str = Form(...), content: str = Form(...)):
    pdf_path = os.path.join(DATA_DIR, f"{uuid.uuid4()}.pdf")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 10, content)
    pdf.output(pdf_path)
    return FileResponse(pdf_path, filename="report.pdf", media_type="application/pdf")

# =====================================================
# SMART CHAT — PUBLIC (no JWT) for demo UI
# =====================================================
@app.post("/api/chat/message_public")
async def chat_message_public(request: Request, question: str = Form(...), lang: str = Form("en")):
    start = time.time()
    sid = _get_sid(request) or secrets.token_hex(16)
    now = datetime.utcnow().isoformat()

    try:
        # Count LLM request
        LLM_REQUESTS_TOTAL.inc()

        reply_core = llm_reply(question)  # OpenAI if available, else local
        hints = differential_diagnosis(question)
        reply = reply_core + ("\n\nPossible conditions (not a diagnosis):\n- " + "\n- ".join(hints))
        reply = translate_text(reply, lang)

        # Approximate token count
        token_count = len(reply.split())
        LLM_TOKENS_TOTAL.inc(token_count)

        USER_ANALYTICS[sid]["messages"] += 1
        SESSIONS[sid].append({"role": "user", "text": question, "time": now})
        SESSIONS[sid].append({"role": "assistant", "text": reply, "time": now})

        return {"ok": True, "reply": reply, "history": list(SESSIONS[sid])}

    finally:
        # Observe latency
        LLM_LATENCY.observe(time.time() - start)

@app.get("/api/chat/history_public")
async def chat_history_public(request: Request):
    sid = _get_sid(request)
    return {"history": list(SESSIONS[sid]) if sid in SESSIONS else []}

@app.post("/api/chat/clear_public")
async def chat_clear_public(request: Request):
    sid = _get_sid(request)
    if sid in SESSIONS:
        SESSIONS[sid].clear()
    return {"ok": True}

# =====================================================
# SMART CHAT — PROTECTED (JWT + DB)
# =====================================================
@app.post("/api/chat/message")
async def chat_message(
    question: str = Form(...),
    lang: str = Form("en"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    start = time.time()
    try:
        if not allow_user_bucket(user.id, time.time()):
            raise HTTPException(429, "Rate limit exceeded")

        # Count LLM request
        LLM_REQUESTS_TOTAL.inc()

        reply_core = llm_reply(question)
        hints = differential_diagnosis(question)
        reply = reply_core + ("\n\nPossible conditions (not a diagnosis):\n- " + "\n- ".join(hints))
        reply = translate_text(reply, lang)

        # Estimate tokens
        token_count = len(reply.split())
        LLM_TOKENS_TOTAL.inc(token_count)

        # Save messages
        db.add(ChatMessage(user_id=user.id, role="user", text=question))
        db.add(ChatMessage(user_id=user.id, role="assistant", text=reply))
        db.commit()

        history = (
            db.query(ChatMessage)
            .filter(ChatMessage.user_id == user.id)
            .order_by(ChatMessage.id.desc())
            .limit(10)
            .all()
        )
        hist = [{"role": m.role, "text": m.text, "time": m.created_at.isoformat()} for m in reversed(history)]
        return {"ok": True, "reply": reply, "history": hist}

    finally:
        # Observe latency
        LLM_LATENCY.observe(time.time() - start)

@app.get("/api/chat/history")
async def chat_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.id.asc())
        .all()
    )
    return {"history": [{"role": m.role, "text": m.text, "time": m.created_at.isoformat()} for m in history]}

@app.post("/api/chat/clear")
async def chat_clear(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(ChatMessage).filter(ChatMessage.user_id == user.id).delete()
    db.commit()
    return {"ok": True}

# =====================================================
# ADMIN USERS API (header token) for UI dashboard
# =====================================================
@app.get("/api/admin/users")
async def api_admin_users(req: Request):
    require_admin_header(req)
    users = [{"sid": sid, **data} for sid, data in USER_ANALYTICS.items()]
    return {"total": len(users), "users": users}

# =====================================================
# UI ROUTES (Home + Tools + Admin) — Phase 2 Branding
# =====================================================
@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(f"""
    <html><body style='background:#0d1117;color:#e6edf3;font-family:sans-serif;padding:24px'>
    <h1>🩺 {APP_TITLE}</h1>

    <h3>🧠 AI Tools</h3>
    <ul>
      <li><a href='/ui/chat/symptoms' style='color:#58a6ff'>💬 Doctor Chat (Public Demo)</a></li>
      <li><a href='/ui/chat/jwt' style='color:#58a6ff'>🔒 Doctor Chat (JWT + DB)</a></li>
      <li><a href='/ui/translate' style='color:#58a6ff'>🌍 Translate Text</a></li>
      <li><a href='/ui/ocr/extract' style='color:#58a6ff'>🔠 OCR Extract</a></li>
      <li><a href='/ui/lab/analyze' style='color:#58a6ff'>🧪 Lab Analyzer</a></li>
      <li><a href='/ui/image/predict' style='color:#58a6ff'>🧠 X-ray Predictor</a></li>
      <li><a href='/ui/dicom/analyze' style='color:#58a6ff'>🩻 DICOM Analyzer</a></li>
      <li><a href='/ui/voice/transcribe' style='color:#58a6ff'>🎙️ Voice Transcribe</a></li>
      <li><a href='/ui/export/pdf' style='color:#58a6ff'>🧾 Export PDF</a></li>
    </ul>

    <h3>👤 Auth (JWT)</h3>
    <ul>
      <li><a href='/ui/auth' style='color:#58a6ff'>🔑 Register / Login</a></li>
    </ul>

    <h3>⚙️ Admin & Analytics</h3>
    <ul>
      <li><a href='/ui/admin/dashboard' style='color:#58a6ff'>📊 Live Admin Dashboard</a></li>
      <li><a href='/ui/admin/users' style='color:#58a6ff'>👥 User Analytics</a></li>
      <li><a href='/admin/portal' style='color:#58a6ff'>⚙️ Admin Portal</a></li>
      <li><a href='/admin/config' style='color:#58a6ff'>📜 /admin/config — Config JSON (Header token)</a></li>
      <li><a href='/admin/metrics/raw' style='color:#58a6ff'>📊 /admin/metrics/raw — Metrics JSON (Header token)</a></li>
      <li><a href='/metrics' style='color:#58a6ff'>📈 /metrics — Prometheus (Public)</a></li>
    </ul>

    <h3>🧪 System</h3>
    <ul>
      <li><a href='/healthz' style='color:#58a6ff'>Health Check</a></li>
      <li><a href='/debug/routes' style='color:#58a6ff'>Debug: View All Routes</a></li>
    </ul>

    <hr style='border:1px solid #30363d;margin-top:20px'>
    <p style='font-size:12px;color:#8b949e'>drhealth © 2025 • Phase 2 Hybrid • FastAPI + ONNX + OpenAI + Prometheus</p>
    </body></html>
    """)

# -------- Public Chat UI (no JWT) --------
@app.get("/ui/chat/symptoms", response_class=HTMLResponse)
async def ui_chat_symptoms():
    return HTMLResponse("""
    <html>
    <body style='background:#0d1117;color:#e6edf3;font-family:sans-serif;padding:24px'>
    <h2>💬 AI Doctor Assistant (Public Demo)</h2>
    <div id='chatBox' style='border:1px solid #30363d;border-radius:8px;padding:10px;width:600px;height:300px;overflow-y:auto;background:#161b22;margin-bottom:10px;'></div>
    <form id='chatForm'>
      <input name='question' id='question' placeholder='Describe symptoms...' style='width:400px;padding:6px;border-radius:6px;border:1px solid #30363d;background:#0d1117;color:#e6edf3'>
      <select name='lang' id='lang'>
        <option value='en'>English</option>
        <option value='hi'>हिन्दी</option>
        <option value='es'>Español</option>
        <option value='fr'>Français</option>
      </select>
      <button type='submit' style='margin-left:8px'>Send</button>
      <button type='button' id='clearBtn' style='margin-left:8px'>Clear</button>
      <button type='button' id='exportBtn' style='margin-left:8px'>Export PDF</button>
    </form>

    <script>
    async function loadHistory(){
        const res = await fetch('/api/chat/history_public');
        const data = await res.json();
        const box = document.getElementById('chatBox');
        box.innerHTML = '';
        data.history.forEach(m => {
          const who = m.role === 'user' ? 'You' : 'Doctor';
          box.innerHTML += `<p><b>${who}:</b> ${m.text}</p>`;
        });
        box.scrollTop = box.scrollHeight;
    }

    document.getElementById('chatForm').onsubmit = async (e)=>{
        e.preventDefault();
        const q = document.getElementById('question').value;
        const lang = document.getElementById('lang').value;
        const form = new FormData();
        form.append('question', q);
        form.append('lang', lang);
        await fetch('/api/chat/message_public', {method:'POST', body: form});
        await loadHistory();
        document.getElementById('question').value = '';
    }

    document.getElementById('clearBtn').onclick = async ()=>{
        await fetch('/api/chat/clear_public', {method:'POST'});
        await loadHistory();
    }

    document.getElementById('exportBtn').onclick = async ()=>{
        const res = await fetch('/api/chat/history_public');
        const data = await res.json();
        let content = data.history.map(m => `${m.role.toUpperCase()}: ${m.text}`).join("\\n\\n");
        const form = new FormData();
        form.append('title', 'Doctor Chat (Public) History');
        form.append('content', content);
        const pdf = await fetch('/api/export/pdf', {method:'POST', body: form});
        const blob = await pdf.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = 'doctor_chat_public.pdf'; a.click();
    }

    loadHistory();
    </script>

    <br><a href='/'>Home</a>
    </body></html>
    """)

# -------- JWT Chat UI (protected) --------
@app.get("/ui/chat/jwt", response_class=HTMLResponse)
async def ui_chat_jwt():
    return HTMLResponse("""
    <html>
    <body style='background:#0d1117;color:#e6edf3;font-family:sans-serif;padding:24px'>
    <h2>🔒 AI Doctor Assistant (JWT + DB)</h2>
    <p style='color:#8b949e'>Paste your Bearer token (from /ui/auth) to use the protected chat.</p>
    <input id='token' placeholder='Paste JWT token' style='width:600px;padding:6px;border-radius:6px;border:1px solid #30363d;background:#0d1117;color:#e6edf3'><br><br>

    <div id='chatBox' style='border:1px solid #30363d;border-radius:8px;padding:10px;width:700px;height:300px;overflow-y:auto;background:#161b22;margin-bottom:10px;'></div>
    <form id='chatForm'>
      <input name='question' id='question' placeholder='Describe symptoms...' style='width:500px;padding:6px;border-radius:6px;border:1px solid #30363d;background:#0d1117;color:#e6edf3'>
      <select name='lang' id='lang'>
        <option value='en'>English</option>
        <option value='hi'>हिन्दी</option>
        <option value='es'>Español</option>
        <option value='fr'>Français</option>
      </select>
      <button type='submit' style='margin-left:8px'>Send</button>
      <button type='button' id='clearBtn' style='margin-left:8px'>Clear</button>
    </form>

    <script>
    function getHeaders(){
      const t = document.getElementById('token').value.trim();
      return t ? {'Authorization': 'Bearer ' + t} : {};
    }

    async function loadHistory(){
        const res = await fetch('/api/chat/history', {headers: getHeaders()});
        if(!res.ok){ alert('Need valid token'); return; }
        const data = await res.json();
        const box = document.getElementById('chatBox');
        box.innerHTML = '';
        data.history.forEach(m => {
          const who = m.role === 'user' ? 'You' : 'Doctor';
          box.innerHTML += `<p><b>${who}:</b> ${m.text}</p>`;
        });
        box.scrollTop = box.scrollHeight;
    }

    document.getElementById('chatForm').onsubmit = async (e)=>{
        e.preventDefault();
        const q = document.getElementById('question').value;
        const lang = document.getElementById('lang').value;
        const form = new FormData();
        form.append('question', q);
        form.append('lang', lang);
        const res = await fetch('/api/chat/message', {method:'POST', body: form, headers: getHeaders()});
        if(!res.ok){ alert('Invalid token or request'); return; }
        await loadHistory();
        document.getElementById('question').value = '';
    }

    document.getElementById('clearBtn').onclick = async ()=>{
        const res = await fetch('/api/chat/clear', {method:'POST', headers: getHeaders()});
        if(!res.ok){ alert('Invalid token'); return; }
        await loadHistory();
    }

    </script>
    <br><a href='/'>Home</a>
    </body></html>
    """)

# -------- Simple Auth UI --------
@app.get("/ui/auth", response_class=HTMLResponse)
async def ui_auth():
    return HTMLResponse("""
    <html><body style='background:#0d1117;color:#e6edf3;font-family:sans-serif;padding:24px'>
    <h2>🔑 Auth — Register / Login</h2>
    <div style='display:flex;gap:24px;flex-wrap:wrap;'>

      <div style='border:1px solid #30363d;border-radius:8px;padding:16px;width:340px;background:#161b22;'>
        <h3>Register</h3>
        <form id='reg'>
          <input name='email' id='reg_email' placeholder='email' style='width:100%;padding:6px;margin-bottom:8px'><br>
          <input name='password' id='reg_password' type='password' placeholder='password' style='width:100%;padding:6px;margin-bottom:8px'><br>
          <button type='submit'>Register</button>
        </form>
        <pre id='reg_out' style='white-space:pre-wrap;margin-top:8px'></pre>
      </div>

      <div style='border:1px solid #30363d;border-radius:8px;padding:16px;width:340px;background:#161b22;'>
        <h3>Login</h3>
        <form id='log'>
          <input name='username' id='log_email' placeholder='email' style='width:100%;padding:6px;margin-bottom:8px'><br>
          <input name='password' id='log_password' type='password' placeholder='password' style='width:100%;padding:6px;margin-bottom:8px'><br>
          <button type='submit'>Login</button>
        </form>
        <pre id='log_out' style='white-space:pre-wrap;margin-top:8px'></pre>
      </div>
    </div>

    <script>
    document.getElementById('reg').onsubmit = async (e)=>{
      e.preventDefault();
      const form = new FormData();
      form.append('email', document.getElementById('reg_email').value);
      form.append('password', document.getElementById('reg_password').value);
      const res = await fetch('/auth/register', {method:'POST', body: form});
      document.getElementById('reg_out').textContent = JSON.stringify(await res.json(), null, 2);
    };

    document.getElementById('log').onsubmit = async (e)=>{
      e.preventDefault();
      const form = new FormData();
      form.append('username', document.getElementById('log_email').value);
      form.append('password', document.getElementById('log_password').value);
      const res = await fetch('/auth/login', {method:'POST', body: form});
      const data = await res.json();
      document.getElementById('log_out').textContent = JSON.stringify(data, null, 2);
      if(data.access_token){
        navigator.clipboard.writeText(data.access_token);
        alert('JWT copied to clipboard. Use it in /ui/chat/jwt');
      }
    };
    </script>

    <br><a href='/'>Home</a>
    </body></html>
    """)

# -------- Other tool UIs (Translate / Voice / OCR / Lab / X-ray / DICOM / PDF / Admin) --------
@app.get("/ui/translate", response_class=HTMLResponse)
async def ui_translate():
    return HTMLResponse("""
    <html><body style='background:#0d1117;color:#e6edf3;font-family:sans-serif;padding:24px'>
    <h2>🌍 Translate Text</h2>
    <form id='form'>
      <textarea name='text' id='text' rows='5' cols='50' placeholder='Enter text to translate'></textarea><br><br>
      <select id='lang'>
        <option value='en'>English</option>
        <option value='hi'>हिन्दी</option>
        <option value='es'>Español</option>
        <option value='fr'>Français</option>
      </select>
      <button type='submit'>Translate</button>
    </form>
    <pre id='output' style='margin-top:16px'></pre>
    <script>
    document.getElementById('form').onsubmit = async (e)=>{
        e.preventDefault();
        const text = document.getElementById('text').value;
        const target_lang = document.getElementById('lang').value;
        const form = new FormData();
        form.append('text', text);
        form.append('target_lang', target_lang);
        const res = await fetch('/api/translate', {method:'POST', body: form});
        const data = await res.json();
        document.getElementById('output').textContent = data.translated;
    };
    </script>
    <br><a href='/'>Home</a>
    </body></html>
    """)

@app.get("/ui/voice/transcribe", response_class=HTMLResponse)
async def ui_voice_transcribe():
    return HTMLResponse("""
    <html><body style='background:#0d1117;color:#e6edf3;font-family:sans-serif;padding:24px'>
    <h2>🎙️ Voice Transcription</h2>
    <form id='form' enctype='multipart/form-data'>
      <input type='file' name='file' id='file' accept='.wav,.mp3' required><br><br>
      <button type='submit'>Upload & Transcribe</button>
    </form>
    <pre id='output' style='margin-top:16px'></pre>
    <script>
    document.getElementById('form').onsubmit = async (e)=>{
        e.preventDefault();
        const file = document.getElementById('file').files[0];
        const form = new FormData();
        form.append('file', file);
        const res = await fetch('/api/voice/transcribe', {method:'POST', body: form});
        const data = await res.json();
        document.getElementById('output').textContent = data.text;
    };
    </script>
    <br><a href='/'>Home</a>
    </body></html>
    """)

@app.get("/ui/ocr/extract", response_class=HTMLResponse)
async def ui_ocr_extract():
    return HTMLResponse("""
    <html><body style='background:#0d1117;color:#e6edf3;font-family:sans-serif;padding:24px'>
    <h2>🔠 OCR Extract</h2>
    <form id='form' enctype='multipart/form-data'>
      <input type='file' name='file' id='file' accept='.png,.jpg,.jpeg,.pdf' required><br><br>
      <button type='submit'>Extract Text</button>
    </form>
    <pre id='output' style='margin-top:16px;white-space:pre-wrap;'></pre>
    <script>
    document.getElementById('form').onsubmit = async (e)=>{
        e.preventDefault();
        const file = document.getElementById('file').files[0];
        const form = new FormData();
        form.append('file', file);
        const res = await fetch('/api/ocr/extract', {method:'POST', body: form});
        const data = await res.json();
        document.getElementById('output').textContent = data.text;
    };
    </script>
    <br><a href='/'>Home</a>
    </body></html>
    """)

@app.get("/ui/lab/analyze", response_class=HTMLResponse)
async def ui_lab_analyze():
    return HTMLResponse("""
    <html><body style='background:#0d1117;color:#e6edf3;font-family:sans-serif;padding:24px'>
    <h2>🧪 Lab Analyzer</h2>
    <form id='form' enctype='multipart/form-data'>
      <input type='file' name='file' id='file' accept='.png,.jpg,.jpeg,.pdf' required><br><br>
      <button type='submit'>Analyze</button>
    </form>
    <h3>Findings:</h3><pre id='findings'></pre>
    <h3>Summary:</h3><pre id='summary'></pre>
    <script>
    document.getElementById('form').onsubmit = async (e)=>{
        e.preventDefault();
        const file = document.getElementById('file').files[0];
        const form = new FormData();
        form.append('file', file);
        const res = await fetch('/api/lab/analyze', {method:'POST', body: form});
        const data = await res.json();
        document.getElementById('findings').textContent = data.findings.join("\\n");
        document.getElementById('summary').textContent = data.summary.join("\\n");
    };
    </script>
    <br><a href='/'>Home</a>
    </body></html>
    """)

@app.get("/ui/image/predict", response_class=HTMLResponse)
async def ui_image_predict():
    return HTMLResponse("""
    <html><body style='background:#0d1117;color:#e6edf3;font-family:sans-serif;padding:24px'>
    <h2>🧠 X-ray Pneumonia Predictor</h2>
    <form id='form' enctype='multipart/form-data'>
      <input type='file' name='file' id='file' accept='.png,.jpg,.jpeg' required><br><br>
      <button type='submit'>Predict</button>
    </form>
    <h3>Result:</h3><pre id='result'></pre>
    <script>
    document.getElementById('form').onsubmit = async (e)=>{
        e.preventDefault();
        const file = document.getElementById('file').files[0];
        const form = new FormData();
        form.append('file', file);
        const res = await fetch('/api/image/predict', {method:'POST', body: form});
        const data = await res.json();
        document.getElementById('result').textContent =
            `Prediction: ${data.prediction}\\nConfidence: ${(data.confidence*100).toFixed(2)}%`;
    };
    </script>
    <br><a href='/'>Home</a>
    </body></html>
    """)

@app.get("/ui/dicom/analyze", response_class=HTMLResponse)
async def ui_dicom_analyze():
    return HTMLResponse("""
    <html><body style='background:#0d1117;color:#e6edf3;font-family:sans-serif;padding:24px'>
    <h2>🩻 DICOM Analyzer</h2>
    <form id='form' enctype='multipart/form-data'>
      <input type='file' name='file' id='file' accept='.dcm' required><br><br>
      <button type='submit'>Analyze</button>
    </form>
    <h3>Metadata:</h3><pre id='meta'></pre>
    <img id='preview' style='max-width:400px;display:none;margin-top:10px;'>
    <script>
    document.getElementById('form').onsubmit = async (e)=>{
        e.preventDefault();
        const file = document.getElementById('file').files[0];
        const form = new FormData();
        form.append('file', file);
        const res = await fetch('/api/dicom/analyze', {method:'POST', body: form});
        const data = await res.json();
        document.getElementById('meta').textContent = JSON.stringify(data.metadata, null, 2);
        if(data.preview){
          const img = document.getElementById('preview');
          img.src = data.preview;
          img.style.display='block';
        }
    };
    </script>
    <br><a href='/'>Home</a>
    </body></html>
    """)

@app.get("/ui/export/pdf", response_class=HTMLResponse)
async def ui_export_pdf():
    return HTMLResponse("""
    <html>
    <body style='background:#0d1117;color:#e6edf3;font-family:sans-serif;padding:24px'>
      <h2>🧾 Export Text to PDF</h2>
      <form id='pdfForm'>
        <label>Title:</label><br>
        <input type='text' id='title' name='title' placeholder='Enter PDF title'
          style='width:400px;padding:6px;margin-bottom:10px;border-radius:6px;
          border:1px solid #30363d;background:#0d1117;color:#e6edf3'><br>
        <label>Content:</label><br>
        <textarea id='content' name='content' rows='10' cols='60' placeholder='Write your content here...'
          style='border-radius:6px;border:1px solid #30363d;background:#0d1117;color:#e6edf3;padding:6px;'></textarea><br><br>
        <button type='submit'
          style='padding:8px 16px;background:#238636;border:none;border-radius:6px;color:white;cursor:pointer;'>
          Generate PDF
        </button>
      </form>
      <br><a href='/' style='color:#58a6ff'>Home</a>

      <script>
      document.getElementById('pdfForm').onsubmit = async (e) => {
          e.preventDefault();
          const title = document.getElementById('title').value.trim();
          const content = document.getElementById('content').value.trim();
          if(!title || !content) {
              alert('Please fill both title and content');
              return;
          }
          const form = new FormData();
          form.append('title', title);
          form.append('content', content);
          const res = await fetch('/api/export/pdf', {method:'POST', body: form});
          if(res.ok) {
              const blob = await res.blob();
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = title.replace(/\\s+/g, '_') + '.pdf';
              document.body.appendChild(a);
              a.click();
              a.remove();
          } else {
              alert('PDF generation failed!');
          }
      }
      </script>
    </body>
    </html>
    """)

@app.get("/admin/portal", response_class=HTMLResponse)
async def admin_portal():
    return HTMLResponse(f"""
    <html><body style='background:#0d1117;color:#e6edf3;font-family:sans-serif;padding:24px'>
    <h2>⚙️ Admin Portal</h2>
    <p>Use your Admin Token (header <code>X-Admin-Token</code>) to access secured APIs.</p>
    <ul>
      <li><a href="/ui/admin/dashboard" style="color:#58a6ff">Live Metrics Dashboard</a></li>
      <li><a href="/ui/admin/users" style="color:#58a6ff">User Analytics</a></li>
      <li><a href="/admin/config" style="color:#58a6ff">API Config (JSON)</a></li>
      <li><a href="/metrics" style="color:#58a6ff">Prometheus Metrics (Raw)</a></li>
    </ul>
    <br><a href="/">Home</a>
    </body></html>
    """)

@app.get("/ui/admin/dashboard", response_class=HTMLResponse)
async def ui_admin_dashboard():
    return HTMLResponse("""
    <html>
    <head><script src="https://cdn.jsdelivr.net/npm/chart.js"></script></head>
    <body style='background:#0d1117;color:#e6edf3;font-family:sans-serif;padding:24px'>
    <h2>📊 Admin Analytics Dashboard</h2>
    <p style='color:#8b949e'>Edit the token inside the JS (default "changeme-super-secret") or set ADMIN_TOKEN env.</p>
    <canvas id="cpuChart" width="400" height="150"></canvas>
    <canvas id="memChart" width="400" height="150"></canvas>
    <canvas id="reqChart" width="400" height="150"></canvas>
    <br><a href='/'>Home</a>
    <script>
    const ADMIN_TOKEN = 'changeme-super-secret';
    const cpuCtx = document.getElementById('cpuChart');
    const memCtx = document.getElementById('memChart');
    const reqCtx = document.getElementById('reqChart');
    let cpuData = [], memData = [], reqData = [], labels = [];
    const cpuChart = new Chart(cpuCtx, {type: 'line', data: {labels, datasets:[{label:'CPU %', data:cpuData}]}});
    const memChart = new Chart(memCtx, {type: 'line', data: {labels, datasets:[{label:'Memory %', data:memData}]}});
    const reqChart = new Chart(reqCtx, {type: 'line', data: {labels, datasets:[{label:'Requests', data:reqData}]}});
    async function refresh(){
      const res = await fetch('/admin/metrics/raw', {headers:{'X-Admin-Token':ADMIN_TOKEN}});
      const d = await res.json();
      const ts = new Date(d.timestamp).toLocaleTimeString();
      labels.push(ts); if(labels.length>10){labels.shift();}
      cpuData.push(d.cpu_percent); if(cpuData.length>10){cpuData.shift();}
      memData.push(d.mem_percent); if(memData.length>10){memData.shift();}
      reqData.push(d.requests_total); if(reqData.length>10){reqData.shift();}
      cpuChart.update(); memChart.update(); reqChart.update();
    }
    setInterval(refresh, 5000); refresh();
    </script></body></html>
    """)

@app.get("/ui/admin/users", response_class=HTMLResponse)
async def ui_admin_users():
    users_html = "".join([
        f"<tr><td>{sid}</td><td>{data['messages']}</td><td>{data['visits']}</td><td>{data['created']}</td></tr>"
        for sid, data in USER_ANALYTICS.items()
    ])
    return HTMLResponse(f"""
    <html><body style='background:#0d1117;color:#e6edf3;font-family:sans-serif;padding:24px'>
    <h2>👥 User Analytics (Public Sessions)</h2>
    <table border='1' cellpadding='6' style='border-collapse:collapse;border:1px solid #30363d; width:100%'>
      <tr><th>SID</th><th>Messages</th><th>Visits</th><th>Created</th></tr>
      {users_html}
    </table><br><a href='/'>Home</a></body></html>
    """)

# =====================================================
# HEALTH & DEBUG
# =====================================================
@app.get("/healthz")
async def healthz():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.get("/debug/routes")
async def debug_routes():
    return {"routes": [r.path for r in app.routes]}

# =====================================================
# MAIN
# =====================================================
if __name__ == "__main__":
    import uvicorn
    print("[OK] drhealth Doctor AI running on http://127.0.0.1:8000")
    uvicorn.run("server_fastapi:app", host="127.0.0.1", port=8000, reload=True)
