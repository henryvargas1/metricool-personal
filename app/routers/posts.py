import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ScheduledPost, Video, Account
from app.schemas import (
    BatchScheduleCreate,
    ScheduledPostOut,
    DashboardStatsOut
)

router = APIRouter(prefix="/api/posts", tags=["Scheduled Posts"])

def format_post_out(post: ScheduledPost) -> ScheduledPostOut:
    return ScheduledPostOut(
        id=post.id,
        video_id=post.video_id,
        account_id=post.account_id,
        account_name=post.account.account_name if post.account else "Cuenta Desconocida",
        platform=post.account.platform if post.account else "Desconocida",
        title=post.title,
        description=post.description,
        hashtags=post.hashtags,
        scheduled_time=post.scheduled_time,
        status=post.status,
        post_url=post.post_url,
        error_detail=post.error_detail,
        retry_count=post.retry_count,
        published_at=post.published_at,
        created_at=post.created_at,
        video_filename=post.video.filename if post.video else None
    )

@router.post("/schedule", response_model=List[ScheduledPostOut], status_code=status.HTTP_201_CREATED)
def schedule_batch(payload: BatchScheduleCreate, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == payload.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="El video seleccionado no existe")
    
    if not payload.targets:
        raise HTTPException(status_code=400, detail="Debes seleccionar al menos una cuenta destino")
    
    created_posts = []
    for target in payload.targets:
        account = db.query(Account).filter(Account.id == target.account_id).first()
        if not account or not account.is_active:
            continue
        
        # Jerarquía: Personalizado > Global
        final_title = target.title if target.title is not None else payload.global_title
        final_desc = target.description if target.description is not None else payload.global_description
        final_tags = target.hashtags if target.hashtags is not None else payload.global_hashtags
        final_time = target.scheduled_time or payload.global_scheduled_time
        
        # Validación de YouTube: requiere título obligatorio
        if account.platform.lower() == "youtube" and not final_title:
            final_title = video.filename.rsplit(".", 1)[0]
        
        post = ScheduledPost(
            video_id=video.id,
            account_id=account.id,
            title=final_title,
            description=final_desc,
            hashtags=final_tags,
            scheduled_time=final_time,
            status="PENDING",
            retry_count=0
        )
        db.add(post)
        created_posts.append(post)
        
    db.commit()
    for p in created_posts:
        db.refresh(p)
        
    return [format_post_out(p) for p in created_posts]

@router.get("", response_model=List[ScheduledPostOut])
def list_posts(
    status_filter: Optional[str] = Query(None, alias="status"),
    platform: Optional[str] = None,
    account_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(ScheduledPost).join(Account)
    
    if status_filter:
        query = query.filter(ScheduledPost.status == status_filter.upper())
    if platform:
        query = query.filter(Account.platform == platform.lower())
    if account_id:
        query = query.filter(ScheduledPost.account_id == account_id)
        
    posts = query.order_by(ScheduledPost.scheduled_time.asc()).all()
    return [format_post_out(p) for p in posts]

@router.get("/stats", response_model=DashboardStatsOut)
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_accounts = db.query(Account).count()
    total_videos = db.query(Video).count()
    total_posts = db.query(ScheduledPost).count()
    pending = db.query(ScheduledPost).filter(ScheduledPost.status == "PENDING").count()
    publishing = db.query(ScheduledPost).filter(ScheduledPost.status == "PUBLISHING").count()
    published = db.query(ScheduledPost).filter(ScheduledPost.status == "PUBLISHED").count()
    failed = db.query(ScheduledPost).filter(ScheduledPost.status == "FAILED").count()
    
    return DashboardStatsOut(
        total_accounts=total_accounts,
        total_videos=total_videos,
        total_posts=total_posts,
        pending_posts=pending,
        publishing_posts=publishing,
        published_posts=published,
        failed_posts=failed
    )

@router.get("/{post_id}", response_model=ScheduledPostOut)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(ScheduledPost).filter(ScheduledPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")
    return format_post_out(post)

@router.post("/{post_id}/retry", response_model=ScheduledPostOut)
def retry_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(ScheduledPost).filter(ScheduledPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")
        
    post.status = "PENDING"
    post.error_detail = None
    post.retry_count += 1
    # Programar para ejecución inmediata
    post.scheduled_time = datetime.datetime.utcnow()
    
    db.commit()
    db.refresh(post)
    return format_post_out(post)

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(ScheduledPost).filter(ScheduledPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")
    db.delete(post)
    db.commit()
    return None
