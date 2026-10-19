import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

# ----------------- ACCOUNTS -----------------
class AccountBase(BaseModel):
    platform: str
    account_name: str
    platform_user_id: Optional[str] = None
    is_active: bool = True

class AccountCreate(AccountBase):
    access_token: str
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime.datetime] = None
    extra_data: Optional[str] = None

class AccountUpdate(BaseModel):
    account_name: Optional[str] = None
    is_active: Optional[bool] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None

class AccountOut(AccountBase):
    id: int
    has_valid_token: bool = True
    token_expires_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# ----------------- VIDEOS -----------------
class VideoOut(BaseModel):
    id: int
    filename: str
    filesize: int
    content_type: str
    duration: Optional[float] = None
    preview_url: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# ----------------- SCHEDULED POSTS -----------------
class TargetAccountSchedule(BaseModel):
    account_id: int
    title: Optional[str] = None
    description: Optional[str] = None
    hashtags: Optional[str] = None
    scheduled_time: Optional[datetime.datetime] = None

class BatchScheduleCreate(BaseModel):
    video_id: int
    global_title: Optional[str] = None
    global_description: Optional[str] = None
    global_hashtags: Optional[str] = None
    global_scheduled_time: datetime.datetime
    targets: List[TargetAccountSchedule]

class ScheduledPostOut(BaseModel):
    id: int
    video_id: int
    account_id: int
    account_name: Optional[str] = None
    platform: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    hashtags: Optional[str] = None
    scheduled_time: datetime.datetime
    status: str
    post_url: Optional[str] = None
    error_detail: Optional[str] = None
    retry_count: int = 0
    published_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    video_filename: Optional[str] = None

    class Config:
        from_attributes = True


# ----------------- DASHBOARD METRICS -----------------
class DashboardStatsOut(BaseModel):
    total_accounts: int
    total_videos: int
    total_posts: int
    pending_posts: int
    publishing_posts: int
    published_posts: int
    failed_posts: int
