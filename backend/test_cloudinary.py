import os, sys, django
sys.path.append("/Users/sunday/Documents/Project/Memory Product/backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
django.setup()

import cloudinary
from apps.core.utils.cloudinary_utils import generate_upload_signature
from django.conf import settings
import requests

try:
    folder = "occasion_gallery/12345678-1234-1234-1234-123456789012"
    sig_data = generate_upload_signature(folder=folder, resource_type="image")
    
    # Let's create a dummy image file
    with open("dummy.png", "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0bIDAT\x08\xd7c\x60\x00\x02\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
    
    # Upload to cloudinary via fetch/requests
    upload_url = f"https://api.cloudinary.com/v1_1/{sig_data['cloud_name']}/image/upload"
    files = {"file": ("dummy.png", open("dummy.png", "rb"), "image/png")}
    data = {
        "api_key": sig_data["api_key"],
        "timestamp": str(sig_data["timestamp"]),
        "signature": sig_data["signature"],
        "folder": sig_data["folder"]
    }
    
    res = requests.post(upload_url, data=data, files=files)
    print("Cloudinary Response Code:", res.status_code)
    print("Cloudinary Response:", res.text)

except Exception as e:
    print("Error:", str(e))
