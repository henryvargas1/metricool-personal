import datetime
import logging
from sqlalchemy.orm import Session
from app.models import ScheduledPost, Account, Video
from app.services.youtube import upload_youtube_video
from app.services.instagram import upload_instagram_reel
from app.services.tiktok import upload_tiktok_video

logger = logging.getLogger("publisher")

def build_full_caption(description: str, hashtags: str) -> str:
    """Une la descripción y los hashtags con salto de línea limpio."""
    desc = (description or "").strip()
    tags = (hashtags or "").strip()
    if desc and tags:
        return f"{desc}\n\n{tags}"
    return desc or tags or ""


def process_single_post(post_id: int, db: Session) -> dict:
    """
    Despacha la publicación de un video programado hacia su red social correspondiente,
    controlando transiciones de estado, tokens y registro de errores.
    """
    post = db.query(ScheduledPost).filter(ScheduledPost.id == post_id).first()
    if not post:
        return {"success": False, "error": "Post no encontrado"}

    account: Account = post.account
    video: Video = post.video

    if not account or not account.is_active:
        post.status = "FAILED"
        post.error_detail = "La cuenta asociada no está activa o fue eliminada"
        db.commit()
        return {"success": False, "error": post.error_detail}

    if not video:
        post.status = "FAILED"
        post.error_detail = "El archivo maestro de video ya no existe en el sistema"
        db.commit()
        return {"success": False, "error": post.error_detail}

    # Marcamos como Publicando
    post.status = "PUBLISHING"
    db.commit()

    full_caption = build_full_caption(post.description, post.hashtags)
    platform = account.platform.lower()

    try:
        result = {}
        if platform == "youtube":
            # Extraer lista de tags limpios
            raw_tags = [t.replace("#", "").strip() for t in (post.hashtags or "").split() if t.strip()]
            
            result = upload_youtube_video(
                filepath=video.filepath,
                title=post.title or video.filename.rsplit(".", 1)[0],
                description=full_caption,
                tags=raw_tags,
                access_token=account.access_token,
                refresh_token=account.refresh_token
            )
            # Si el token se refrescó durante la subida, lo persistimos
            if result.get("refreshed_access_token"):
                account.access_token = result["refreshed_access_token"]
                if result.get("token_expires_at"):
                    account.token_expires_at = result["token_expires_at"]

        elif platform == "instagram":
            if not account.platform_user_id:
                raise ValueError("Falta el Instagram Business User ID en la cuenta configurada")
                
            result = upload_instagram_reel(
                filepath=video.filepath,
                caption=full_caption,
                ig_user_id=account.platform_user_id,
                access_token=account.access_token
            )

        elif platform == "tiktok":
            result = upload_tiktok_video(
                filepath=video.filepath,
                title=full_caption or post.title or "Nuevo video",
                access_token=account.access_token
            )

        else:
            raise ValueError(f"Plataforma '{platform}' no soportada")

        # Éxito: Actualizar post
        post.status = "PUBLISHED"
        post.post_url = result.get("post_url")
        post.platform_post_id = result.get("platform_post_id")
        post.published_at = datetime.datetime.utcnow()
        post.error_detail = None
        db.commit()

        return {
            "success": True,
            "post_id": post.id,
            "platform": platform,
            "post_url": post.post_url
        }

    except Exception as exc:
        logger.error(f"Error publicando post {post_id} en {platform}: {str(exc)}", exc_info=True)
        post.status = "FAILED"
        post.error_detail = str(exc)
        db.commit()
        return {
            "success": False,
            "post_id": post.id,
            "platform": platform,
            "error": str(exc)
        }
