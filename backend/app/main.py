from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.automation import router as automation_router
from app.routes.discovery import router as discovery_router
from app.routes.leads import router as leads_router
from app.services.agent_scheduler import start_agent_scheduler, stop_agent_scheduler
from app.services.lead_store import init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    start_agent_scheduler()
    try:
        yield
    finally:
        stop_agent_scheduler()


app = FastAPI(title="Lead Agent API", version="0.5.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leads_router)
app.include_router(discovery_router)
app.include_router(automation_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "lead-agent-api", "version": "0.5.0"}
