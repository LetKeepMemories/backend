import logging
import json

logger = logging.getLogger(__name__)

class ErrorTrackingMiddleware:
    """
    Middleware that captures HTTP status codes 400 and above,
    logging the request details and the response payload.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # We need to capture the request body before it gets consumed.
        # However, for large file uploads (multipart), reading request.body might fail or consume too much memory.
        request_body = None
        if request.method in ["POST", "PUT", "PATCH"] and request.content_type == "application/json":
            try:
                request_body = request.body.decode("utf-8")
            except Exception:
                request_body = "<Could not decode request body>"

        response = self.get_response(request)

        if response.status_code >= 400:
            # Safely attempt to get the response payload
            response_payload = None
            if hasattr(response, 'data'):
                # DRF responses usually have a .data attribute
                response_payload = response.data
            else:
                try:
                    response_payload = response.content.decode("utf-8")
                except Exception:
                    response_payload = "<Could not decode response content>"

            log_data = {
                "status_code": response.status_code,
                "path": request.path,
                "method": request.method,
                "user": str(request.user) if hasattr(request, "user") else "Anonymous",
                "request_body": request_body,
                "response_payload": response_payload,
            }
            error_str = f"HTTP Error {response.status_code} at {request.path}: {json.dumps(log_data, default=str)}\n"
            logger.error(error_str)
            with open("error_log.txt", "a") as f:
                f.write(error_str)

        return response
