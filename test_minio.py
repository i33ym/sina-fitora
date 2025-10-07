import pytest
from fastapi.testclient import TestClient
from main import app
from io import BytesIO

client = TestClient(app)


def test_upload_image():
    # Create fake image file
    image_data = b"fake image data"
    files = {
        "file": ("test.jpg", BytesIO(image_data), "image/jpeg")
    }
    
    response = client.post(
        "/images/upload",
        files=files,
        headers={"Authorization": "Bearer YOUR_TOKEN"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "filename" in data
    assert "url" in data
    print(f"✅ Upload test passed: {data['filename']}")


def test_get_image():
    # First upload
    image_data = b"fake image data"
    files = {
        "file": ("test.jpg", BytesIO(image_data), "image/jpeg")
    }
    
    upload_response = client.post(
        "/images/upload",
        files=files,
        headers={"Authorization": "Bearer YOUR_TOKEN"}
    )
    
    image_id = upload_response.json()["id"]
    
    # Then get
    response = client.get(f"/images/{image_id}")
    assert response.status_code == 200
    print("✅ Get image test passed")