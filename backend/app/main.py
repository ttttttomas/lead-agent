from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.leads import router as leads_router

app = FastAPI(title="Lead Agent API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leads_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "lead-agent-api"}
