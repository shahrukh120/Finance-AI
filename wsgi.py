"""
WSGI entry point for production deployment.
Run with: gunicorn wsgi:app
"""

from app import app

if __name__ == "__main__":
    app.run()
