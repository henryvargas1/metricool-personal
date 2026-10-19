import os
import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from app.config import settings

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/userinfo.profile"
]

def get_youtube_service(access_token: str, refresh_token: str = None):
    """
    Construye un cliente autenticado de YouTube con capacidad de refresco de token.
    """
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.YOUTUBE_CLIENT_ID,
        client_secret=settings.YOUTUBE_CLIENT_SECRET,
        scopes=YOUTUBE_SCOPES
    )

    # Si el token expiró y tenemos refresh_token, lo renovamos automáticamente
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    service = build("youtube", "v3", credentials=creds, cache_discovery=False)
    return service, creds


def upload_youtube_video(
    filepath: str,
    title: str,
    description: str,
    tags: list = None,
    privacy_status: str = "public",
    access_token: str = "",
    refresh_token: str = None
) -> dict:
    """
    Sube un video a YouTube usando el protocolo oficial Resumable Upload (óptimo para videos largos).
    Retorna diccionario con id del video y URL directa.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Archivo de video no encontrado en: {filepath}")

    service, updated_creds = get_youtube_service(access_token, refresh_token)

    body = {
        "snippet": {
            "title": title[:100],  # Límite de YouTube: 100 caracteres
            "description": description or "",
            "tags": tags or [],
            "categoryId": "22"  # Categoría por defecto: People & Blogs
        },
        "status": {
            "privacyStatus": privacy_status,  # 'public', 'private', 'unlisted'
            "selfDeclaredMadeForKids": False
        }
    }

    # Chunks de 5 MB para subidas estables y reanudables
    media = MediaFileUpload(
        filepath,
        chunksize=5 * 1024 * 1024,
        resumable=True
    )

    try:
        request = service.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            # Si se desea monitorear progreso: status.progress()

        video_id = response.get("id")
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        return {
            "platform_post_id": video_id,
            "post_url": video_url,
            "refreshed_access_token": updated_creds.token,
            "token_expires_at": updated_creds.expiry
        }

    except HttpError as e:
        error_msg = f"Error en YouTube API (HTTP {e.resp.status}): {e.content.decode('utf-8') if e.content else str(e)}"
        raise RuntimeError(error_msg)
    except Exception as e:
        raise RuntimeError(f"Fallo al subir a YouTube: {str(e)}")
