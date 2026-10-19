import urllib.parse
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import Account

router = APIRouter(prefix="/api/auth", tags=["OAuth & Accounts Connection"])

# ==================== YOUTUBE (GOOGLE OAUTH2) ====================

@router.get("/youtube/url")
def get_youtube_auth_url():
    """Genera la URL de autorización OAuth2 oficial de Google para YouTube."""
    if not settings.YOUTUBE_CLIENT_ID:
        raise HTTPException(status_code=400, detail="Falta configurar YOUTUBE_CLIENT_ID en .env")
    
    params = {
        "client_id": settings.YOUTUBE_CLIENT_ID,
        "redirect_uri": settings.YOUTUBE_REDIRECT_URI,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/userinfo.profile",
        "access_type": "offline",  # Crucial para recibir refresh_token
        "prompt": "consent"
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return {"url": auth_url}


@router.get("/youtube/callback")
def youtube_callback(code: str = Query(...), db: Session = Depends(get_db)):
    """Intercambia el código por tokens y registra el canal de YouTube en la BD."""
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": settings.YOUTUBE_CLIENT_ID,
        "client_secret": settings.YOUTUBE_CLIENT_SECRET,
        "redirect_uri": settings.YOUTUBE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    with httpx.Client(timeout=15.0) as client:
        res = client.post(token_url, data=token_data)
        if res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Fallo al intercambiar token con Google: {res.text}")
        
        token_info = res.json()
        access_token = token_info.get("access_token")
        refresh_token = token_info.get("refresh_token")

        # Consultar canal del usuario autenticado
        channel_name = "Canal de YouTube"
        channel_id = None
        try:
            yt_res = client.get(
                "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if yt_res.status_code == 200:
                yt_data = yt_res.json()
                items = yt_data.get("items", [])
                if items:
                    channel_id = items[0]["id"]
                    channel_name = items[0]["snippet"]["title"]
        except Exception:
            pass

    # Guardar o actualizar cuenta en SQLite
    account = db.query(Account).filter(Account.platform == "youtube", Account.platform_user_id == channel_id).first()
    if not account:
        account = Account(
            platform="youtube",
            account_name=channel_name,
            platform_user_id=channel_id,
            access_token=access_token,
            refresh_token=refresh_token,
            is_active=True
        )
        db.add(account)
    else:
        account.account_name = channel_name
        account.access_token = access_token
        if refresh_token:
            account.refresh_token = refresh_token
        account.is_active = True

    db.commit()
    # Redireccionar al panel principal
    return RedirectResponse(url="/?account_connected=youtube")


# ==================== META (INSTAGRAM REELS) ====================

@router.get("/meta/url")
def get_meta_auth_url():
    """Genera la URL de autorización oficial de Meta para Instagram Business."""
    if not settings.META_APP_ID:
        raise HTTPException(status_code=400, detail="Falta configurar META_APP_ID en .env")

    params = {
        "client_id": settings.META_APP_ID,
        "redirect_uri": settings.META_REDIRECT_URI,
        "scope": "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement",
        "response_type": "code"
    }
    auth_url = f"https://www.facebook.com/v19.0/dialog/oauth?{urllib.parse.urlencode(params)}"
    return {"url": auth_url}


@router.get("/meta/callback")
def meta_callback(code: str = Query(...), db: Session = Depends(get_db)):
    """Intercambia código por token de larga duración y vincula cuentas de Instagram."""
    token_url = "https://graph.facebook.com/v19.0/oauth/access_token"
    params = {
        "client_id": settings.META_APP_ID,
        "client_secret": settings.META_APP_SECRET,
        "redirect_uri": settings.META_REDIRECT_URI,
        "code": code
    }

    with httpx.Client(timeout=20.0) as client:
        res = client.get(token_url, params=params)
        if res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Fallo al autenticar con Meta: {res.text}")

        short_token = res.json().get("access_token")

        # Intercambiar por token de larga duración (60 días)
        long_token_res = client.get(
            f"https://graph.facebook.com/v19.0/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "fb_exchange_token": short_token
            }
        )
        final_token = long_token_res.json().get("access_token", short_token) if long_token_res.status_code == 200 else short_token

        # Buscar las cuentas de Instagram vinculadas a las Páginas de Facebook del usuario
        pages_res = client.get(
            f"https://graph.facebook.com/v19.0/me/accounts?fields=name,access_token,instagram_business_account{{id,username,name}}&access_token={final_token}"
        )

        connected_count = 0
        if pages_res.status_code == 200:
            pages = pages_res.json().get("data", [])
            for p in pages:
                ig_info = p.get("instagram_business_account")
                if ig_info:
                    ig_id = ig_info.get("id")
                    username = ig_info.get("username", p.get("name"))
                    # El page token o el user long-lived token sirve para publicar
                    page_token = p.get("access_token", final_token)

                    account = db.query(Account).filter(Account.platform == "instagram", Account.platform_user_id == ig_id).first()
                    if not account:
                        account = Account(
                            platform="instagram",
                            account_name=f"@{username}",
                            platform_user_id=ig_id,
                            access_token=page_token,
                            is_active=True
                        )
                        db.add(account)
                    else:
                        account.account_name = f"@{username}"
                        account.access_token = page_token
                        account.is_active = True
                    connected_count += 1
        
        db.commit()

    return RedirectResponse(url=f"/?account_connected=instagram&count={connected_count}")


# ==================== TIKTOK ====================

@router.get("/tiktok/url")
def get_tiktok_auth_url():
    """Genera la URL de autorización oficial de TikTok v2."""
    if not settings.TIKTOK_CLIENT_KEY:
        raise HTTPException(status_code=400, detail="Falta configurar TIKTOK_CLIENT_KEY en .env")

    params = {
        "client_key": settings.TIKTOK_CLIENT_KEY,
        "scope": "user.info.basic,video.upload,video.publish",
        "response_type": "code",
        "redirect_uri": settings.TIKTOK_REDIRECT_URI
    }
    auth_url = f"https://www.tiktok.com/v2/auth/authorize/?{urllib.parse.urlencode(params)}"
    return {"url": auth_url}


@router.get("/tiktok/callback")
def tiktok_callback(code: str = Query(...), db: Session = Depends(get_db)):
    """Intercambia código por token y vincula perfil de TikTok."""
    token_url = "https://open.tiktokapis.com/v2/oauth/token/"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "client_key": settings.TIKTOK_CLIENT_KEY,
        "client_secret": settings.TIKTOK_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.TIKTOK_REDIRECT_URI
    }

    with httpx.Client(timeout=20.0) as client:
        res = client.post(token_url, headers=headers, data=data)
        if res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Fallo al autenticar con TikTok: {res.text}")

        res_json = res.json()
        token_info = res_json.get("data", res_json)
        access_token = token_info.get("access_token")
        refresh_token = token_info.get("refresh_token")
        open_id = token_info.get("open_id")

        # Obtener nombre público
        display_name = f"TikTok_{open_id[:8]}" if open_id else "Cuenta TikTok"
        try:
            info_res = client.get(
                "https://open.tiktokapis.com/v2/user/info/?fields=display_name,avatar_url",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if info_res.status_code == 200:
                user_data = info_res.json().get("data", {}).get("user", {})
                if user_data.get("display_name"):
                    display_name = f"@{user_data['display_name']}"
        except Exception:
            pass

    account = db.query(Account).filter(Account.platform == "tiktok", Account.platform_user_id == open_id).first()
    if not account:
        account = Account(
            platform="tiktok",
            account_name=display_name,
            platform_user_id=open_id,
            access_token=access_token,
            refresh_token=refresh_token,
            is_active=True
        )
        db.add(account)
    else:
        account.account_name = display_name
        account.access_token = access_token
        if refresh_token:
            account.refresh_token = refresh_token
        account.is_active = True

    db.commit()
    return RedirectResponse(url="/?account_connected=tiktok")
