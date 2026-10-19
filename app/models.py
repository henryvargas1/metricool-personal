import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.database import Base

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, index=True)  # 'youtube', 'instagram', 'tiktok'
    account_name = Column(String(100), nullable=False)        # ej: '@mi_marca_reels'
    platform_user_id = Column(String(100), nullable=True)     # ID interno de la plataforma (ej. IG User ID)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    extra_data = Column(Text, nullable=True)                  # JSON con datos adicionales (avatar, page_id, etc.)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relaciones
    scheduled_posts = relationship("ScheduledPost", back_populates="account", cascade="all, delete-orphan")


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)            # Nombre original del archivo
    stored_filename = Column(String(255), nullable=False)     # Nombre guardado en disco
    filepath = Column(String(500), nullable=False)            # Ruta absoluta/relativa
    filesize = Column(Integer, nullable=False)                # Tamaño en bytes
    content_type = Column(String(100), nullable=False)        # video/mp4, video/quicktime, etc.
    duration = Column(Float, nullable=True)                   # Duración en segundos si se calcula
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relaciones
    scheduled_posts = relationship("ScheduledPost", back_populates="video", cascade="all, delete-orphan")


class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    
    # Matriz de copys
    title = Column(String(255), nullable=True)               # Obligatorio en YouTube, opcional en IG/TikTok
    description = Column(Text, nullable=True)                # Descripción o pie de video
    hashtags = Column(String(500), nullable=True)            # Etiquetas adicionales
    
    # Control de tiempo y estado
    scheduled_time = Column(DateTime, nullable=False, index=True) # Momento exacto de publicación
    status = Column(String(50), default="PENDING", index=True)    # PENDING, PUBLISHING, PUBLISHED, FAILED, CANCELLED
    
    # Resultado de publicación
    post_url = Column(String(500), nullable=True)            # Enlace público resultante del video publicado
    platform_post_id = Column(String(100), nullable=True)    # ID devuelto por la API
    error_detail = Column(Text, nullable=True)               # Detalle en caso de error
    retry_count = Column(Integer, default=0)                 # Veces que se ha reintentado
    
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relaciones
    video = relationship("Video", back_populates="scheduled_posts")
    account = relationship("Account", back_populates="scheduled_posts")
