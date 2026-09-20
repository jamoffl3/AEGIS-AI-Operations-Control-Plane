"""
AEGIS — AWS Lambda Adapter

Thin AWS entry point for the existing FastAPI application.

API Gateway
    ↓
Lambda
    ↓
Mangum
    ↓
FastAPI
    ↓
AEGIS application/control plane
"""

from mangum import Mangum

from services.api.main import app


handler = Mangum(app)