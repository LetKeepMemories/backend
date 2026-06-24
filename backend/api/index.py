"""
Vercel serverless entry point.
Vercel's @vercel/python builder looks for a module-level `app` or `handler`
variable in this file. We simply re-export the Django WSGI application.
"""
import sys
import os

# Ensure the backend root is on the path so Django settings resolve correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.wsgi import application  # noqa: E402

app = application
