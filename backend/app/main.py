from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import alerts, investigate

settings = get_settings()

app = FastAPI(title="AI SOC Analyst")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alerts.router)
app.include_router(investigate.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
