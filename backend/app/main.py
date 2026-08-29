from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.discovery import router as discovery_router
from app.routes.leads import router as leads_router
from app.services.lead_store import init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield


app = FastAPI(title="Lead Agent API", version="0.4.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leads_router)
app.include_router(discovery_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "lead-agent-api", "version": "0.4.0"}
