import os
import time
import math
import httpx
from typing import Dict, Any, Optional
from app.config import settings

TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"

def refresh_tiktok_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    """
    Renueva el token de acceso de TikTok usando el refresh_token.
    """
    url = f"{TIKTOK_API_BASE}/oauth/token/"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "client_key": settings.TIKTOK_CLIENT_KEY,
        "client_secret": settings.TIKTOK_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, headers=headers, data=data)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


def upload_tiktok_video(
    filepath: str,
    title: str,
    access_token: str,
    privacy_level: str = "PUBLIC_TO_EVERYONE",
    disable_duet: bool = False,
    disable_stitch: bool = False,
    disable_comment: bool = False
) -> Dict[str, Any]:
    """
    Publica un video en TikTok usando la Content Posting API v2:
    1. Inicializa la sesión con post_info y source_info (chunks).
    2. Sube los bloques de video al upload_url de TikTok con Content-Range.
    3. Sondea status_fetch hasta confirmar publicación exitosa.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Video no encontrado en: {filepath}")

    filesize = os.path.getsize(filepath)
    # Tamaño de chunk recomendado por TikTok: entre 5MB y 64MB (excepto el último)
    chunk_size = 10 * 1024 * 1024  # 10MB
    total_chunks = math.ceil(filesize / chunk_size)

    with httpx.Client(timeout=60.0) as client:
        # Paso 1: Inicialización
        init_url = f"{TIKTOK_API_BASE}/post/publish/video/init/"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        }
        init_payload = {
            "post_info": {
                "title": title[:2200],  # Límite de TikTok
                "privacy_level": privacy_level,
                "disable_duet": disable_duet,
                "disable_stitch": disable_stitch,
                "disable_comment": disable_comment
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": filesize,
                "chunk_size": chunk_size if total_chunks > 1 else filesize,
                "total_chunk_count": total_chunks
            }
        }

        init_resp = client.post(init_url, headers=headers, json=init_payload)
        if init_resp.status_code != 200:
            raise RuntimeError(f"Error iniciando publicación en TikTok (HTTP {init_resp.status_code}): {init_resp.text}")

        res_json = init_resp.json()
        error_info = res_json.get("error", {})
        if error_info.get("code") != "ok":
            raise RuntimeError(f"Error de TikTok API: {error_info.get('message', 'Desconocido')} ({res_json})")

        data = res_json.get("data", {})
        publish_id = data.get("publish_id")
        upload_url = data.get("upload_url")

        if not publish_id or not upload_url:
            raise RuntimeError(f"Respuesta de inicialización inválida de TikTok: {res_json}")

        # Paso 2: Subida de chunks
        with open(filepath, "rb") as vf:
            for chunk_idx in range(total_chunks):
                start = chunk_idx * chunk_size
                chunk_data = vf.read(chunk_size)
                end = start + len(chunk_data) - 1

                chunk_headers = {
                    "Content-Range": f"bytes {start}-{end}/{filesize}",
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(chunk_data))
                }

                upload_resp = client.put(upload_url, headers=chunk_headers, content=chunk_data)
                if upload_resp.status_code not in (200, 201, 206):
                    raise RuntimeError(f"Error al subir chunk {chunk_idx + 1}/{total_chunks} a TikTok: {upload_resp.text}")

        # Paso 3: Sondeo de estado (polling)
        status_url = f"{TIKTOK_API_BASE}/post/publish/status_fetch/"
        poll_payload = {"publish_id": publish_id}

        max_attempts = 25
        published = False
        post_url = None

        for _ in range(max_attempts):
            time.sleep(5)
            status_resp = client.post(status_url, headers=headers, json=poll_payload)
            if status_resp.status_code != 200:
                continue

            status_data = status_resp.json().get("data", {})
            status = status_data.get("status")

            if status == "PUBLISH_COMPLETE":
                published = True
                # Si TikTok retorna enlace o IDs públicos
                public_id = status_data.get("publicaly_available_post_id", [None])[0] if status_data.get("publicaly_available_post_id") else None
                if public_id:
                    post_url = f"https://www.tiktok.com/@post/video/{public_id}"
                break
            elif status == "FAILED":
                fail_reason = status_data.get("fail_reason", "Razón no especificada")
                raise RuntimeError(f"TikTok rechazó la publicación: {fail_reason}")

        if not published:
            # En TikTok a veces toma más tiempo la moderación; dejamos registrado el publish_id
            post_url = f"https://www.tiktok.com (Procesándose con Publish ID: {publish_id})"

        return {
            "platform_post_id": publish_id,
            "post_url": post_url or f"https://www.tiktok.com (Publish ID: {publish_id})"
        }
