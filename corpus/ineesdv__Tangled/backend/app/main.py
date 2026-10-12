from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routers import auth_routes, core_routes
from .routers import config_routes
from .database import Base, engine, SessionLocal
from .models import User
from .auth import hash_password
import threading
from .worker import scheduled_watcher, shutdown_worker, worker_health_check
from sqlalchemy import text
from .config import settings
import signal
from os import _exit

WORKER_SHUTDOWN_TIMEOUT = getattr(settings, 'worker_shutdown_timeout', 10)

app = FastAPI(title="Tangled API")

origins = [o.strip() for o in settings.api_cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(core_routes.router)
app.include_router(config_routes.router)

def openapi_spec():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Tangled API",
        version="0.1.0",
        routes=app.routes,
    )
    
    openapi_schema["tags"] = [
        {"name": "Auth", "description": "Authentication and authorization"},
        {"name": "Config", "description": "Application configuration and settings"},
        {"name": "API", "description": "Main endpoints"},
        {"name": "Sender profiles", "x-parent": "API", "description": "Manage email sender identities"},
        {"name": "Servers", "x-parent": "API", "description": "SMTP server configuration"},
        {"name": "Target lists", "x-parent": "API", "description": "Recipient management"},
        {"name": "Templates", "x-parent": "API", "description": "Email template creation and editing"},
        {"name": "Campaigns", "x-parent": "API", "description": "Campaign execution and analytics"},
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = openapi_spec

stop_event = threading.Event()
watcher_thread = None
shutdown_in_progress = False

def handle_shutdown_signal(signum, frame):
    global shutdown_in_progress
    
    if shutdown_in_progress:
        return
    
    shutdown_in_progress = True
    print(f"\n[main] SHUTDOWN SIGNAL RECEIVED (signal {signum})", flush=True)
    
    try:
        shutdown_event()
    except Exception as e:
        print(f"[main] Error during shutdown: {e}", flush=True)
    
    print("[main] Exiting now...", flush=True)
    _exit(0)

signal.signal(signal.SIGTERM, handle_shutdown_signal)
signal.signal(signal.SIGINT, handle_shutdown_signal)

@app.on_event("startup")
def startup_seed_and_watch():
    global watcher_thread
    
    Base.metadata.create_all(bind=engine)

    if settings.admin_email and settings.admin_password:
        db = SessionLocal()
        try:
            exists = db.query(User).filter(User.email==settings.admin_email).first()
            if not exists:
                u = User(email=settings.admin_email, password_hash=hash_password(settings.admin_password))
                db.add(u)
                db.commit()
        finally:
            db.close()
    
    watcher_thread = threading.Thread(target=scheduled_watcher, args=(stop_event,), daemon=False)
    watcher_thread.start()
    print("[main] Worker started successfully", flush=True)

@app.on_event("shutdown")
def shutdown_event():
    global watcher_thread
    
    print("[main] Shutdown signal received", flush=True)
    shutdown_worker(stop_event, timeout=WORKER_SHUTDOWN_TIMEOUT)
    
    if watcher_thread and watcher_thread.is_alive():
        print("[main] Waiting for watcher thread to stop...", flush=True)
        watcher_thread.join(timeout=10)
    
    print("[main] Shutdown complete", flush=True)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/worker/health")
def worker_health():
    return worker_health_check()