import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Video
from app.schemas import VideoOut
from app.config import settings

router = APIRouter(prefix="/api/videos", tags=["Videos"])

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v"}
ALLOWED_MIME_TYPES = {"video/mp4", "video/quicktime", "video/webm", "video/x-m4v"}

def build_video_out(video: Video) -> VideoOut:
    return VideoOut(
        id=video.id,
        filename=video.filename,
        filesize=video.filesize,
        content_type=video.content_type,
        duration=video.duration,
        preview_url=f"/api/videos/{video.id}/stream",
        created_at=video.created_at
    )

@router.post("/upload", response_model=VideoOut, status_code=status.HTTP_201_CREATED)
async def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    original_filename = file.filename or "video.mp4"
    extension = os.path.splitext(original_filename)[1].lower()
    
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no permitido ({extension}). Formatos soportados: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}{extension}"
    target_path = os.path.join(settings.UPLOAD_DIR, unique_name)
    
    # Escribir archivo por bloques (chunks) para no saturar memoria RAM con videos grandes
    filesize = 0
    try:
        with open(target_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024 * 4):  # 4MB chunks
                buffer.write(chunk)
                filesize += len(chunk)
    except Exception as e:
        if os.path.exists(target_path):
            os.remove(target_path)
        raise HTTPException(status_code=500, detail=f"Error guardando el video: {str(e)}")
    
    content_type = file.content_type or "video/mp4"
    
    video = Video(
        filename=original_filename,
        stored_filename=unique_name,
        filepath=target_path,
        filesize=filesize,
        content_type=content_type,
        duration=None
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    
    return build_video_out(video)

@router.get("", response_model=List[VideoOut])
def list_videos(db: Session = Depends(get_db)):
    videos = db.query(Video).order_by(Video.created_at.desc()).all()
    return [build_video_out(v) for v in videos]

@router.get("/{video_id}", response_model=VideoOut)
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video no encontrado")
    return build_video_out(video)

@router.get("/{video_id}/stream")
def stream_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video no encontrado")
    
    if not os.path.exists(video.filepath):
        raise HTTPException(status_code=404, detail="El archivo físico de video no existe")
        
    return FileResponse(
        path=video.filepath,
        media_type=video.content_type,
        filename=video.filename
    )

@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video no encontrado")
        
    if os.path.exists(video.filepath):
        try:
            os.remove(video.filepath)
        except OSError:
            pass
            
    db.delete(video)
    db.commit()
    return None
