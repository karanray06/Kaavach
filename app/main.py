import os
import logging
import datetime
import hashlib
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Form, UploadFile, File, Request, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

import io
from PIL import Image, ImageOps, UnidentifiedImageError
from app.config import GEMINI_MODEL_ID
from app.pipeline import run_scan, MEMORY_STORE, MEMORY_STORE_LOCK
from app.snow import check_health, get_trending_tactics, get_recent_campaigns, get_snowflake_connection
from app.trends import get_cached_trends, set_cached_trends, calculate_trend_metrics

load_dotenv()
logger = logging.getLogger("kavach.main")

Image.MAX_IMAGE_PIXELS = 25_000_000
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIMES = {"image/png", "image/jpeg", "image/webp"}

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Kavach API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS configuration (defaults to same-origin only unless CORS_ALLOWED_ORIGINS is set)
cors_origins_env = os.environ.get("CORS_ALLOWED_ORIGINS", "")
allowed_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.mount("/static", StaticFiles(directory="web"), name="static")

def detect_image_magic(header: bytes) -> Optional[str]:
    """
    Validates file magic bytes to ensure genuine image uploads.
    """
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
        return "image/webp"
    return None

@app.get("/")
async def root():
    return FileResponse("web/index.html")

@app.get("/scan")
async def scan_page():
    return FileResponse("web/scan.html")

@app.get("/radar")
async def radar_page():
    return FileResponse("web/radar.html")

@app.get("/drill")
async def drill_page():
    return FileResponse("web/drill.html")

@app.get("/api/health")
async def health_check():
    snowflake_status = check_health()
    return JSONResponse(content={
        "status": "ok",
        "model": GEMINI_MODEL_ID,
        "snowflake": snowflake_status,
        "dataset": "stub_dataset"
    })

@app.get("/api/trends")
async def api_trends():
    cached = get_cached_trends()
    if cached is not None:
        return JSONResponse(content=cached)

    trends = get_trending_tactics()
    if trends is not None:
        set_cached_trends(trends)
        return JSONResponse(content=trends)
    
    # Fallback to MEMORY_STORE
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff_7d = now - datetime.timedelta(days=7)
    cutoff_14d = now - datetime.timedelta(days=14)

    total_scans_7d = 0
    ai_unavail_7d = 0
    curr_tactics = {}
    prev_tactics = {}

    with MEMORY_STORE_LOCK:
        for s in MEMORY_STORE["scans"].values():
            if s.get("is_demo", False):
                continue
            ts_str = s.get("ts")
            scan_time = None
            if ts_str:
                try:
                    scan_time = datetime.datetime.fromisoformat(ts_str)
                    if scan_time.tzinfo is None:
                        scan_time = scan_time.replace(tzinfo=datetime.timezone.utc)
                except Exception:
                    scan_time = now
            else:
                scan_time = now

            tactic = s.get("primary_tactic")
            if not tactic and s.get("tactics"):
                t_list = s.get("tactics")
                if isinstance(t_list, list) and len(t_list) > 0 and isinstance(t_list[0], dict):
                    tactic = t_list[0].get("code")

            if scan_time >= cutoff_7d:
                total_scans_7d += 1
                if not s.get("ai_available", True) or s.get("verdict") == "UNCERTAIN" or not tactic or tactic in ("UNKNOWN", ""):
                    ai_unavail_7d += 1
                if tactic and tactic not in ("UNKNOWN", ""):
                    curr_tactics[tactic] = curr_tactics.get(tactic, 0) + 1
            elif scan_time >= cutoff_14d:
                if tactic and tactic not in ("UNKNOWN", ""):
                    prev_tactics[tactic] = prev_tactics.get(tactic, 0) + 1

    mem_trends = calculate_trend_metrics(
        curr_tactics=curr_tactics,
        prev_tactics=prev_tactics,
        total_scans=total_scans_7d,
        ai_unavailable_count=ai_unavail_7d,
        source="memory"
    )
    set_cached_trends(mem_trends)
    return JSONResponse(content=mem_trends)

@app.get("/api/campaigns")
async def api_campaigns():
    campaigns = get_recent_campaigns()
    if campaigns is not None:
        return JSONResponse(content={"source": "snowflake", "campaigns": campaigns})
    
    # Fallback to MEMORY_STORE
    camp_list = []
    with MEMORY_STORE_LOCK:
        for cid, cdata in MEMORY_STORE["campaigns"].items():
            if str(cid).startswith("C-DEMO"):
                continue
            tactic = cdata.get("primary_tactic", "UNKNOWN")
            camp_list.append({
                "campaign_id": cid,
                "variant_count": int(cdata.get("variant_count", 1)),
                "top_tactic": tactic,
                "primary_tactic": tactic,
                "first_seen": str(cdata.get("first_seen", "unknown")),
                "last_seen": str(cdata.get("last_seen", "unknown"))
            })
    camp_list.sort(key=lambda x: str(x.get("last_seen", "")), reverse=True)
    return JSONResponse(content={"source": "memory", "campaigns": camp_list[:5]})

@app.get("/api/drill/sample")
async def drill_sample():
    """
    Returns recent campaign or scan sample (redacted) for training drill.
    """
    conn = get_snowflake_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT s.scan_id, s.primary_tactic, s.campaign_id, i.ioc_display
                FROM SCANS s
                LEFT JOIN INDICATORS i ON s.scan_id = i.scan_id
                WHERE s.is_demo = FALSE AND s.verdict IN ('SUSPICIOUS', 'LIKELY_SCAM')
                ORDER BY s.ts DESC LIMIT 1
            """)
            row = cur.fetchone()
            cur.close()
            if row:
                tactic = row[1] if row[1] and row[1] != "UNKNOWN" else "FAKE_KYC"
                ioc = row[3] if row[3] else "http://sbi-verify.example.invalid"
                text = f"Dear customer, your bank account requires urgent verification for {tactic}. Click here: {ioc}"
                return JSONResponse(content={
                    "source": "snowflake",
                    "tactic": tactic,
                    "text": text,
                    "red_flags": ["urgent verification", ioc],
                    "campaign_id": row[2]
                })
        except Exception as e:
            logger.warning("Failed to query drill sample from Snowflake: %s", e)

    with MEMORY_STORE_LOCK:
        for s in reversed(list(MEMORY_STORE["scans"].values())):
            if s.get("verdict") in ("SUSPICIOUS", "LIKELY_SCAM"):
                tactics = s.get("tactics", [])
                tactic = tactics[0].get("code", "FAKE_KYC") if tactics and isinstance(tactics[0], dict) else "FAKE_KYC"
                inds = s.get("indicators", [])
                ioc = inds[0].get("display", "http://sbi-verify.example.invalid") if inds else "http://sbi-verify.example.invalid"
                text = f"Dear customer, your bank account requires urgent verification for {tactic}. Click here: {ioc}"
                return JSONResponse(content={
                    "source": "memory",
                    "tactic": tactic,
                    "text": text,
                    "red_flags": ["urgent verification", ioc],
                    "campaign_id": s.get("campaign", {}).get("id") if s.get("campaign") else None
                })

    return JSONResponse(content={
        "source": "default",
        "tactic": "FAKE_KYC",
        "text": "Dear customer, your bank account requires urgent verification. Click here: http://sbi-verify.example.invalid",
        "red_flags": ["urgent verification", "http://sbi-verify.example.invalid"],
        "campaign_id": None
    })

@app.post("/api/scan")
@limiter.limit("20/minute")
async def scan(
    request: Request,
    background_tasks: BackgroundTasks,
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    lang: str = Form("en")
):
    # Check Content-Length header against 10MB limit (+64KB form-data boundary allowance)
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_IMAGE_SIZE + (64 * 1024):
                return JSONResponse(status_code=413, content={"error": "Payload exceeds 10MB limit"})
        except ValueError:
            pass

    # Cap text length to 5000 characters
    if text and len(text) > 5000:
        return JSONResponse(status_code=400, content={"error": "Text exceeds maximum limit of 5000 characters"})

    image_bytes = None
    mime_type = "image/png"
    if image:
        # Read MAX + 1 bytes to prevent unbounded RAM usage
        raw_bytes = await image.read(MAX_IMAGE_SIZE + 1)
        if len(raw_bytes) > MAX_IMAGE_SIZE:
            return JSONResponse(status_code=413, content={"error": "Image file exceeds 10MB limit"})
            
        detected_mime = detect_image_magic(raw_bytes[:16])
        if not detected_mime or detected_mime not in ALLOWED_MIMES:
            return JSONResponse(status_code=400, content={"error": "Invalid image format. Allowed: PNG, JPEG, WebP"})
        
        # Pillow Preprocessing: verify, fix EXIF orientation, convert RGB, downscale to 1600px, re-encode JPEG q85, strip EXIF
        try:
            img = Image.open(io.BytesIO(raw_bytes))
            img.verify()
            img = Image.open(io.BytesIO(raw_bytes))
            img = ImageOps.exif_transpose(img) or img
            if img.mode != "RGB":
                img = img.convert("RGB")
            w, h = img.size
            longest = max(w, h)
            if longest > 1600:
                scale = 1600.0 / longest
                new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            out_buf = io.BytesIO()
            img.save(out_buf, format="JPEG", quality=85, optimize=True)
            image_bytes = out_buf.getvalue()
            mime_type = "image/jpeg"
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as err:
            logger.warning("Corrupt or invalid image upload: %s", err)
            return JSONResponse(status_code=400, content={"error": "Corrupt or unreadable image file"})

    # If there's neither text nor image, reject with 400
    if not text and not image_bytes:
        return JSONResponse(status_code=400, content={"error": "Must provide either text or image"})
    today_salt = datetime.datetime.now().strftime("%Y-%m-%d")
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    raw = f"{client_ip}:{user_agent}:{today_salt}"
    client_id = hashlib.sha256(raw.encode()).hexdigest()

    try:
        result = run_scan(
            text=text or "",
            image_bytes=image_bytes,
            mime_type=mime_type,
            lang=lang,
            client_id=client_id,
            background_tasks=background_tasks
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error("Scan processing encountered an unhandled exception: %s", e)
        return JSONResponse(status_code=500, content={"error": "Internal scan processing error"})

