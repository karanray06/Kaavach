import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from unittest.mock import patch
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

def test_scan_corrupt_image():
    # Valid magic bytes but corrupted body
    corrupt_png = b"\x89PNG\r\n\x1a\n" + b"\x00\x01\x02\x03\x04\x05corrupt"
    response = client.post(
        "/api/scan",
        data={"text": "checking scam"},
        files={"image": ("corrupt.png", io.BytesIO(corrupt_png), "image/png")}
    )
    assert response.status_code == 400
    assert "Corrupt or unreadable image file" in response.json()["error"]

def test_scan_oversized_image():
    # File larger than 10MB
    large_payload = b"\x89PNG\r\n\x1a\n" + (b"\x00" * (10 * 1024 * 1024 + 10))
    response = client.post(
        "/api/scan",
        data={"text": "checking scam"},
        files={"image": ("large.png", io.BytesIO(large_payload), "image/png")}
    )
    assert response.status_code == 413
    assert "exceeds 10MB limit" in response.json()["error"]

def test_scan_valid_pillow_image_preprocessing():
    # Create valid 1800x1200 image in memory (should be downscaled to 1600 on longest side)
    img = Image.new("RGBA", (1800, 1200), color=(255, 0, 0, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    with patch("app.pipeline.classify_text_and_image") as mock_classify:
        mock_classify.return_value = '{"is_scam_likelihood": 0.1, "tactics": [], "impersonated_entity_type": "none", "channel_guess": "unknown", "reasoning_short": "Safe", "actions": []}'
        response = client.post(
            "/api/scan",
            data={"text": "sample check"},
            files={"image": ("photo.png", io.BytesIO(png_bytes), "image/png")}
        )
        assert response.status_code == 200
        assert "scan_id" in response.json()

def test_trends_and_campaigns_endpoints():
    r_trends = client.get("/api/trends")
    assert r_trends.status_code == 200
    assert "trends" in r_trends.json()

    r_campaigns = client.get("/api/campaigns")
    assert r_campaigns.status_code == 200
    assert "campaigns" in r_campaigns.json()

def test_drill_sample_endpoint():
    r_drill = client.get("/api/drill/sample")
    assert r_drill.status_code == 200
    data = r_drill.json()
    assert "text" in data
    assert "tactic" in data
    assert "red_flags" in data
