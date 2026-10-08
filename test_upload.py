import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_scan_empty_payload():
    # Neither text nor image provided
    response = client.post("/api/scan", data={})
    assert response.status_code == 400
    assert "Must provide either text or image" in response.json()["error"]

def test_scan_text_length_cap():
    long_text = "A" * 5001
    response = client.post("/api/scan", data={"text": long_text})
    assert response.status_code == 400
    assert "5000 characters" in response.json()["error"]

def test_scan_invalid_image_magic_bytes():
    fake_png = b"NOT_A_REAL_PNG_HEADER_DATA"
    response = client.post(
        "/api/scan",
        data={"text": "checking scam"},
        files={"image": ("test.png", io.BytesIO(fake_png), "image/png")}
    )
    assert response.status_code == 400
    assert "Invalid image format" in response.json()["error"]

def test_scan_oversized_image():
    # File larger than 5MB
    large_payload = b"\x89PNG\r\n\x1a\n" + (b"\x00" * (5 * 1024 * 1024 + 10))
    response = client.post(
        "/api/scan",
        data={"text": "checking scam"},
        files={"image": ("large.png", io.BytesIO(large_payload), "image/png")}
    )
    assert response.status_code == 413
    assert "exceeds 5MB limit" in response.json()["error"]

def test_trends_and_campaigns_endpoints():
    r_trends = client.get("/api/trends")
    assert r_trends.status_code == 200
    assert "trends" in r_trends.json()

    r_campaigns = client.get("/api/campaigns")
    assert r_campaigns.status_code == 200
    assert "campaigns" in r_campaigns.json()
