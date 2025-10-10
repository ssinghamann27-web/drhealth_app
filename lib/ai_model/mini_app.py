from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time
from fastapi import Request

app = FastAPI()

# ---- Prometheus metrics
REQ_COUNT = Counter("api_requests_total", "Total API requests", ["endpoint","method","status"])
REQ_LATENCY = Histogram("api_request_latency_seconds", "Request latency (s)", ["endpoint"])
INPROGRESS = Gauge("api_inprogress", "In-progress requests")

@app.middleware("http")
async def _metrics_mw(request: Request, call_next):
    start = time.time()
    INPROGRESS.inc()
    try:
        response = await call_next(request)
        status = getattr(response, "status_code", 500)
    except Exception:
        status = 500
        from fastapi.responses import JSONResponse
        response = JSONResponse({"detail":"Server error"}, status_code=500)
    finally:
        INPROGRESS.dec()
        REQ_COUNT.labels(request.url.path, request.method, str(status)).inc()
        REQ_LATENCY.labels(request.url.path).observe(time.time()-start)
    return response

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse("<html><body><h1>drhealth</h1><ul><li><a href='/admin/portal'>/admin/portal</a></li><li><a href='/metrics'>/metrics</a></li></ul></body></html>")

@app.get("/admin/portal", response_class=HTMLResponse)
async def admin_portal():
    return HTMLResponse("<html><body><h2>Admin Portal</h2><ul><li><a href='/metrics' target='_blank'>/metrics</a></li></ul><p>Protected routes would require X-Admin-Token header.</p></body></html>")

@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    return PlainTextResponse(generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST)
