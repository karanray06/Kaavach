from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv
from typing import Optional
from app.pipeline import run_scan
from app.snow import check_health

load_dotenv()

app = FastAPI(title="Kavach API")
app.mount("/static", StaticFiles(directory="web"), name="static")

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
        "model": os.environ.get("GEMINI_MODEL_ID", "gemini-3.1-pro-preview"),
        "snowflake": snowflake_status,
        "dataset": "stub_dataset" # Stub for now
    })

@app.post("/api/scan")
async def scan(
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    lang: str = Form("en")
):
    image_bytes = await image.read() if image else None
    
    # If there's no text and no image, return an error
    if not text and not image_bytes:
        return JSONResponse(status_code=400, content={"error": "Must provide either text or image"})
        
    result = run_scan(text or "", image_bytes=image_bytes, lang=lang)
    return JSONResponse(content=result)
