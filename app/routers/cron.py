import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ScheduledPost
from app.config import settings

from app.services.scheduler import check_and_publish_pending_posts

router = APIRouter(prefix="/api/cron", tags=["Cron Automation"])

@router.get("/trigger")
def trigger_cron(
    secret: Optional[str] = Query(None),
    x_cron_secret: Optional[str] = Header(None)
):
    provided_secret = secret or x_cron_secret
    
    # Validación básica de seguridad para evitar invocaciones no autorizadas
    if settings.CRON_SECRET and provided_secret != settings.CRON_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Secreto de cron inválido o ausente"
        )
    
    # Ejecuta el procesador de publicaciones pendientes
    execution_result = check_and_publish_pending_posts()
    
    return {
        "status": "success",
        "result": execution_result
    }

