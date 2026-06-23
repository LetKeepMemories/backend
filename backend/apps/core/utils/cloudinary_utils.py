import time

import cloudinary
import cloudinary.utils
from django.conf import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)


def generate_upload_signature(*, folder: str, resource_type: str = "auto") -> dict:
    """Sign a direct browser-to-Cloudinary upload.

    The API secret never leaves the server: we sign a timestamp + folder
    here, the browser uploads straight to Cloudinary with that signature,
    and Django only ever sees the resulting URL/metadata afterwards. This
    keeps large media off our own request/response cycle entirely.
    """
    timestamp = int(time.time())
    params_to_sign = {"timestamp": timestamp, "folder": folder}
    signature = cloudinary.utils.api_sign_request(params_to_sign, settings.CLOUDINARY_API_SECRET)
    return {
        "signature": signature,
        "timestamp": timestamp,
        "api_key": settings.CLOUDINARY_API_KEY,
        "cloud_name": settings.CLOUDINARY_CLOUD_NAME,
        "folder": folder,
        "resource_type": resource_type,
    }
