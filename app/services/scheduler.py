import datetime
import threading
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal
from app.models import ScheduledPost
from app.services.publisher import process_single_post

logger = logging.getLogger("scheduler")

# Candado en memoria para evitar que dos ejecuciones simultáneas procesen el mismo post
_lock = threading.Lock()
scheduler = BackgroundScheduler(daemon=True)

def check_and_publish_pending_posts() -> dict:
    """
    Función central del motor:
    1. Obtiene el candado de ejecución para evitar condiciones de carrera.
    2. Busca en SQLite todas las publicaciones pendientes cuya fecha/hora programada sea <= ahora.
    3. Procesa y despacha cada una hacia su conector de API respectivo.
    """
    if not _lock.acquire(blocking=False):
        logger.info("El ciclo de publicación ya está en ejecución por otro hilo/cron. Omitiendo ciclo actual.")
        return {"status": "skipped", "reason": "lock_acquired_by_another_process"}

    db = SessionLocal()
    processed_count = 0
    success_count = 0
    failed_count = 0

    try:
        now = datetime.datetime.utcnow()
        # Buscamos publicaciones pendientes cuya hora ya haya llegado
        due_posts = (
            db.query(ScheduledPost)
            .filter(
                ScheduledPost.status == "PENDING",
                ScheduledPost.scheduled_time <= now
            )
            .order_by(ScheduledPost.scheduled_time.asc())
            .all()
        )

        for post in due_posts:
            processed_count += 1
            logger.info(f"Procesando publicación #{post.id} para la cuenta {post.account_id}...")
            
            # Ejecución protegida
            result = process_single_post(post.id, db)
            if result.get("success"):
                success_count += 1
            else:
                failed_count += 1

        return {
            "status": "completed",
            "timestamp": now.isoformat(),
            "found_due_posts": processed_count,
            "success": success_count,
            "failed": failed_count
        }

    except Exception as e:
        logger.error(f"Error inesperado en check_and_publish_pending_posts: {str(e)}", exc_info=True)
        return {"status": "error", "error": str(e)}

    finally:
        db.close()
        _lock.release()


def start_scheduler():
    """Inicia el motor de tareas en segundo plano que revisa cada minuto."""
    if not scheduler.running:
        scheduler.add_job(
            check_and_publish_pending_posts,
            trigger="interval",
            seconds=60,
            id="publish_due_posts_job",
            replace_existing=True,
            coalesce=True,
            max_instances=1
        )
        scheduler.start()
        logger.info("Motor de programación APScheduler iniciado (verificación cada 60s).")


def shutdown_scheduler():
    """Detiene limpiamente el motor de tareas."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Motor de programación APScheduler detenido.")
