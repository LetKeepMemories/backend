import logging

import resend
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_email(*, to: str, subject: str, template: str, context: dict) -> None:
    """Render an HTML template under templates/emails/ and send it via Resend.

    Failures are logged rather than raised so a flaky email provider never
    breaks the request that triggered it (signup, payment, etc.) — callers
    that need delivery guarantees should invoke this from a Celery task.
    """
    html = render_to_string(f"emails/{template}", context)

    if not settings.RESEND_API_KEY:
        # No provider configured (e.g. local dev) — log instead of failing,
        # so the verification/reset link is still visible for testing.
        logger.info("RESEND_API_KEY not set; printing email instead of sending.\nTo: %s\nSubject: %s\n%s", to, subject, html)
        return

    resend.api_key = settings.RESEND_API_KEY
    try:
        resend.Emails.send(
            {
                "from": settings.DEFAULT_FROM_EMAIL,
                "to": [to],
                "subject": subject,
                "html": html,
            }
        )
    except Exception:
        logger.exception("Failed to send email %s to %s", template, to)
