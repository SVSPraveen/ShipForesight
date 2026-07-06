from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from backend.config import get_settings

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Allow health checks without API key
        if request.url.path == "/health":
            return await call_next(request)
            
        settings = get_settings()
        api_key = request.headers.get("X-API-Key")
        
        if not api_key or api_key != settings.api_key:
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
            
        response = await call_next(request)
        return response
