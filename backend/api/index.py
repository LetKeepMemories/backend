"""
Vercel serverless entry point.
Vercel's functions runtime looks for a module-level `app` variable.
"""
import sys
import os

# Ensure the backend root is on the path so Django settings resolve correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config.wsgi import application
    app = application
except Exception as e:
    # Surface startup errors as HTTP 500 so they're visible in Vercel logs
    import traceback
    _startup_error = traceback.format_exc()

    def app(environ, start_response):
        start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
        return [f"Django startup error:\n{_startup_error}".encode()]
