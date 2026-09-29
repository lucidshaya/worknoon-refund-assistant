import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the backend directory (one level above app/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import ai
from .routers import admin, refunds
from .seed_data import init_db

# Initialize (and seed, if empty) the database as soon as the module is
# imported. This runs both under uvicorn and under TestClient/pytest,
# whereas a startup-event hook only fires when the app is actually served,
# which TestClient doesn't always do without an explicit `with` block.
init_db(reset=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(reset=False)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="WORKNOON Refund Assistant",
    description="AI-assisted, policy-enforced e-commerce refund processing.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # take-home assessment scope; would be locked down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(refunds.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "ai_available": ai.ai_available()}
