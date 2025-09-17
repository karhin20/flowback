from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from database import init_db
from routers import customers, actions, sms, upload, websocket, templates, auth
from config.settings import settings

# Load environment variables
load_dotenv()

# Configuration is automatically validated when settings is instantiated
# No need for manual validation

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Insight Ops Flow Backend",
    description="Backend API for the Insight Ops Flow application",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Include routers
app.include_router(customers.router, prefix="/api/customers", tags=["customers"])
app.include_router(actions.router, prefix="/api/actions", tags=["actions"])
app.include_router(sms.router, prefix="/api/sms", tags=["sms"])
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(websocket.router, tags=["websocket"])
app.include_router(templates.router, prefix="/api/templates", tags=["Templates"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

@app.get("/")
async def root():
    return {"message": "Insight Ops Flow Backend API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
