from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.alerts import store
from app.alerts.generators import generate_alert, generate_random_alert
from app.alerts.models import Alert, AlertType
from app.ratelimit import enforce_generate_limit

router = APIRouter(prefix="/alerts", tags=["alerts"])


class GenerateAlertRequest(BaseModel):
    type: AlertType | None = None  # omit to get a random alert type


@router.get("/types")
def list_alert_types() -> list[AlertType]:
    return list(AlertType)


@router.get("")
def list_alerts() -> list[Alert]:
    return store.list_all()


@router.get("/{alert_id}")
def get_alert(alert_id: str) -> Alert:
    alert = store.get(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="alert not found")
    return alert


@router.post("/generate", dependencies=[Depends(enforce_generate_limit)])
def generate(body: GenerateAlertRequest = GenerateAlertRequest()) -> Alert:
    alert = generate_alert(body.type) if body.type else generate_random_alert()
    return store.save(alert)
