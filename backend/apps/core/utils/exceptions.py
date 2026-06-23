import logging

from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    """Wrap DRF's default handler so every error response has a consistent
    `{"detail": ..., "errors": {...}}` shape the frontend can rely on.
    """
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled exception in %s", context.get("view"))
        return response

    data = response.data
    if isinstance(data, dict) and "detail" in data and len(data) == 1:
        response.data = {"detail": data["detail"]}
    else:
        response.data = {"detail": "Validation failed.", "errors": data}
    return response
