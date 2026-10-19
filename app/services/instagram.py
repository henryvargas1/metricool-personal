import os
import time
import httpx
from typing import Optional, Dict, Any

GRAPH_API_VERSION = "v19.0"
GRAPH_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

def refresh_instagram_long_lived_token(access_token: str) -> Optional[str]:
    """
    Renueva un token de larga duración de Instagram (válido por 60 días adicionales).
    """
    url = f"https://graph.instagram.com/refresh_access_token"
    params = {
        "grant_type": "ig_refresh_token",
        "access_token": access_token
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("access_token")
    except Exception:
        pass
    return None


def upload_instagram_reel(
    filepath: str,
    caption: str,
    ig_user_id: str,
    access_token: str,
    share_to_feed: bool = True
) -> Dict[str, Any]:
    """
    Publica un video en Instagram Reels usando la API oficial de Meta Graph:
    1. Inicia sesión de subida reanudable para REELS.
    2. Transfiere el archivo binario del video.
    3. Sondea (polling) hasta que el contenedor procese el video ('FINISHED').
    4. Dispara media_publish para publicar el Reel.
    5. Obtiene el permalink público resultante.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Video no encontrado en: {filepath}")

    filesize = os.path.getsize(filepath)

    with httpx.Client(timeout=60.0) as client:
        # Paso 1: Crear el contenedor de subida reanudable para Reels
        init_url = f"{GRAPH_BASE_URL}/{ig_user_id}/media"
        init_params = {
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": caption or "",
            "share_to_feed": "true" if share_to_feed else "false",
            "access_token": access_token
        }

        init_resp = client.post(init_url, data=init_params)
        if init_resp.status_code != 200:
            raise RuntimeError(f"Error iniciando contenedor de Instagram Reel: {init_resp.text}")

        init_data = init_resp.json()
        container_id = init_data.get("id")
        upload_uri = init_data.get("uri")

        if not container_id or not upload_uri:
            raise RuntimeError(f"Respuesta inesperada de Meta API: {init_data}")

        # Paso 2: Subir el archivo binario al endpoint RUPLOAD de Meta
        upload_headers = {
            "Authorization": f"OAuth {access_token}",
            "offset": "0",
            "file_size": str(filesize),
            "Content-Type": "application/octet-stream"
        }

        with open(filepath, "rb") as video_file:
            video_bytes = video_file.read()

        upload_resp = client.post(upload_uri, headers=upload_headers, content=video_bytes)
        if upload_resp.status_code not in (200, 201):
            raise RuntimeError(f"Error subiendo bytes del Reel a Meta: {upload_resp.text}")

        # Paso 3: Monitorear el procesamiento del contenedor (transcodificación)
        status_url = f"{GRAPH_BASE_URL}/{container_id}"
        max_attempts = 30  # Hasta ~2.5 minutos de sondeo
        processed = False

        for _ in range(max_attempts):
            time.sleep(5)
            status_resp = client.get(
                status_url,
                params={"fields": "status_code,status", "access_token": access_token}
            )
            if status_resp.status_code != 200:
                continue

            status_info = status_resp.json()
            code = status_info.get("status_code")

            if code == "FINISHED":
                processed = True
                break
            elif code in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"Meta reportó fallo al procesar el Reel: {status_info}")

        if not processed:
            raise TimeoutError("Tiempo de espera agotado mientras Instagram procesaba el video")

        # Paso 4: Publicar el Reel oficialmente
        publish_url = f"{GRAPH_BASE_URL}/{ig_user_id}/media_publish"
        publish_resp = client.post(
            publish_url,
            data={"creation_id": container_id, "access_token": access_token}
        )
        if publish_resp.status_code != 200:
            raise RuntimeError(f"Error al ejecutar media_publish en Instagram: {publish_resp.text}")

        published_media_id = publish_resp.json().get("id")

        # Paso 5: Obtener permalink público
        permalink = None
        if published_media_id:
            try:
                media_info_resp = client.get(
                    f"{GRAPH_BASE_URL}/{published_media_id}",
                    params={"fields": "permalink", "access_token": access_token}
                )
                if media_info_resp.status_code == 200:
                    permalink = media_info_resp.json().get("permalink")
            except Exception:
                pass

        if not permalink:
            permalink = f"https://www.instagram.com/reel/{published_media_id}/"

        return {
            "platform_post_id": published_media_id,
            "post_url": permalink
        }
