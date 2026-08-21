"""Pydantic API contracts shared by the HTTP boundary and tests.

Keeping transport schemas in this package makes the application entrypoint smaller
without changing its public import compatibility.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LoginIn(BaseModel):
    email: EmailStr
    password: str

class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str

class TokenOut(BaseModel):
    token: str
    email: str
    role: str

class Category(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    slug: str
    name: str
    description: str = ""
    image_url: str = ""
    order: int = 0

class CategoryIn(BaseModel):
    name: str
    description: str = ""
    image_url: str = ""
    order: int = 0
    slug: Optional[str] = None

class Chapter(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str = ""
    order: int = 0
    is_preview: bool = False
    has_images: bool = False
    image_count: int = 0
    word_count: int = 0
    reading_minutes: int = 0
    language_hint: str = ""
    processing_status: str = "ready"
    processing_error: str = ""
    processing_warnings: List[str] = Field(default_factory=list)
    source_filename: str = ""
    uploaded_at: str = ""
    updated_at: str = ""

class ChapterIn(BaseModel):
    title: str
    content: str = ""
    is_preview: bool = False

class ChapterReorderIn(BaseModel):
    ids: List[str]

class Book(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    slug: str
    title: str
    subtitle: str = ""
    author: str = "The Earnalism"
    category_slug: str
    short_description: str = ""
    description: str = ""
    cover_url: str = ""
    cover_image_url: str = ""
    thumbnail_url: str = ""
    blur_placeholder: str = ""
    dominant_color: str = ""
    back_cover_url: str = ""
    back_cover_image_url: str = ""
    back_cover_thumbnail_url: str = ""
    back_cover_blur_placeholder: str = ""
    back_cover_dominant_color: str = ""
    cover_processing_status: str = ""
    cover_processing_error: str = ""
    back_cover_processing_status: str = ""
    back_cover_processing_error: str = ""
    cover_width: int = 0
    cover_height: int = 0
    cover_sha256: str = ""
    cover_audit_status: str = ""
    cover_updated_at: str = ""
    cover_updated_by: str = ""
    back_cover_width: int = 0
    back_cover_height: int = 0
    back_cover_sha256: str = ""
    back_cover_audit_status: str = ""
    back_cover_updated_at: str = ""
    back_cover_updated_by: str = ""
    estimated_reading_time: str = ""
    price_paperback: str = ""
    price_ebook: str = ""
    buy_url: str = ""
    formats: List[str] = Field(default_factory=lambda: ["Paperback", "Ebook"])
    benefits: List[str] = Field(default_factory=list)
    who_for: List[str] = Field(default_factory=list)
    learnings: List[str] = Field(default_factory=list)
    about_author: str = ""
    chapters: List[Chapter] = Field(default_factory=list)
    audiobook_enabled: bool = False
    generate_audiobook: bool = False
    audiobook_provider: str = ""
    audiobook_voice: str = ""
    audiobook_assets_updated_at: str = ""
    audio_asset_slug: str = ""
    audiobook_assets: Dict[str, str] = Field(default_factory=dict)
    audiobook: Dict[str, Any] = Field(default_factory=dict)
    language: str = ""
    language_code: str = ""
    editorial_shelf_ids: List[str] = Field(default_factory=list)
    home_shelf_ids: List[str] = Field(default_factory=list)
    home_feature_eligible: bool = True
    home_shelf_rank: Optional[int] = None
    admin_pinned: bool = False
    do_not_feature: bool = False
    popularity_score: Optional[float] = None
    sprint_id: str = ""
    rights_metadata: Dict[str, Any] = Field(default_factory=dict)
    readerStatus: str = "ready_for_editorial_review"
    publicationStatus: str = "draft"
    isPublic: bool = False
    isLive: bool = False
    showInPublicLibrary: bool = False
    showInHomepage: bool = False
    allowPublicReading: bool = False
    allowCheckout: bool = False
    allowPayment: bool = False
    is_published: bool = False
    created_at: str = Field(default_factory=now_iso)


class PublicChapterOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = ""
    title: str = ""
    order: int = 0
    is_preview: bool = False
    has_images: bool = False
    image_count: int = 0
    word_count: int = 0
    reading_minutes: int = 0
    language_hint: str = ""
    processing_status: str = ""
    processing_warnings: List[str] = Field(default_factory=list)
    source_filename: str = ""
    uploaded_at: str = ""
    updated_at: str = ""


class PublicBookOut(BaseModel):
    """Safe public book shape for controlled-launch catalog/detail routes."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    slug: str = ""
    title: str = ""
    subtitle: str = ""
    author: str = ""
    category_slug: str = ""
    short_description: str = ""
    description: str = ""
    cover_url: str = ""
    cover_image_url: str = ""
    thumbnail_url: str = ""
    blur_placeholder: str = ""
    dominant_color: str = ""
    back_cover_url: str = ""
    back_cover_image_url: str = ""
    back_cover_thumbnail_url: str = ""
    back_cover_blur_placeholder: str = ""
    back_cover_dominant_color: str = ""
    estimated_reading_time: str = ""
    formats: List[str] = Field(default_factory=list)
    benefits: List[str] = Field(default_factory=list)
    who_for: List[str] = Field(default_factory=list)
    learnings: List[str] = Field(default_factory=list)
    about_author: str = ""
    chapters: List[PublicChapterOut] = Field(default_factory=list)
    is_published: bool = False
    created_at: str = ""
    updated_at: str = ""
    publication_status: str = ""
    launch_status: str = ""
    reader_enabled: bool = False
    preview_enabled: bool = False
    audio_enabled: bool = False
    audiobook_enabled: bool = False
    audiobook_assets: Dict[str, str] = Field(default_factory=dict)
    audiobook: Optional[Dict[str, Any]] = None
    public_route: str = ""
    reader_url: str = ""
    preview_url: str = ""
    audio_url: str = ""
    audio_status: str = ""
    audiobook_release_gate: str = ""
    audio_qa_status: str = ""
    cta_label: str = ""
    secondary_cta_label: str = ""
    public_json_ld_enabled: bool = False
    source_note: str = ""
    rights_note: str = ""


class BookIn(BaseModel):
    title: str
    subtitle: str = ""
    author: str = "The Earnalism"
    category_slug: str
    short_description: str = ""
    description: str = ""
    cover_image_url: str = ""
    back_cover_image_url: str = ""
    estimated_reading_time: str = ""
    price_paperback: str = ""
    price_ebook: str = ""
    buy_url: str = ""
    formats: List[str] = Field(default_factory=lambda: ["Paperback", "Ebook"])
    benefits: List[str] = Field(default_factory=list)
    who_for: List[str] = Field(default_factory=list)
    learnings: List[str] = Field(default_factory=list)
    about_author: str = ""
    rights_metadata: Dict[str, Any] = Field(default_factory=dict)
    source_url: str = ""
    source_name: str = ""
    source_license: str = ""
    source_hash: str = ""
    content_hash: str = ""
    provenance_hash: str = ""
    rights_basis: str = ""
    rights_tier: str = ""
    verification_status: str = ""
    qa_status: str = ""
    approved_to_publish: bool = False
    publication_status: str = ""
    audiobook_enabled: bool = False
    generate_audiobook: bool = False
    readerStatus: str = "ready_for_editorial_review"
    publicationStatus: str = "draft"
    isPublic: bool = False
    isLive: bool = False
    showInPublicLibrary: bool = False
    showInHomepage: bool = False
    allowPublicReading: bool = False
    allowCheckout: bool = False
    allowPayment: bool = False
    is_published: bool = False
    slug: Optional[str] = None


class HomeCurationIn(BaseModel):
    editorial_shelf_ids: Optional[List[str]] = None
    home_shelf_ids: Optional[List[str]] = None
    home_feature_eligible: Optional[bool] = None
    home_shelf_rank: Optional[int] = None
    admin_pinned: Optional[bool] = None
    do_not_feature: Optional[bool] = None
    popularity_score: Optional[float] = None


class CoverPromotionIn(BaseModel):
    kind: str
    candidate_sha256: str = Field(min_length=64, max_length=64)
    approval_decision: str
    editorial_approved: bool = False
    rights_cleared: bool = False
    approval_note: str = Field(min_length=8, max_length=2000)
    rights_basis: str = Field(min_length=8, max_length=2000)


class BookAudiobookIn(BaseModel):
    audiobook_enabled: bool = True
    generate_audiobook: bool = True
    audiobook_provider: str = ""
    audiobook_voice: str = ""
    audio_asset_slug: str = ""
    audiobook_assets: Dict[str, str] = Field(default_factory=dict)
    audiobook_size: int = 0
    audiobook_duration_ms: int = 0


class AudiobookPresignIn(BaseModel):
    audio_object_key: str = Field(min_length=1, max_length=300)
    audio_sha256: str = Field(default="", max_length=71)
    audio_md5: str = Field(default="", max_length=128)
    evidence_object_key: str = Field(default="", max_length=300)
    expires_in: int = Field(default=600, ge=60, le=900)


class AudiobookReleaseIn(BaseModel):
    """Compact, server-verifiable release receipt from the audio runner."""

    audio_object_key: str = Field(min_length=1, max_length=300)
    audio_sha256: str = Field(min_length=64, max_length=71)
    audio_size_bytes: int = Field(gt=0)
    duration_seconds: float = Field(gt=0)
    manuscript_sha256: str = Field(min_length=64, max_length=71)
    provider: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=160)
    voice: str = Field(min_length=1, max_length=120)
    attempt_fingerprint: str = Field(default="", max_length=71)
    qa: Dict[str, Any] = Field(default_factory=dict)
    owner_public_release_intent: bool = False
    release_request_id: str = Field(default="", max_length=160)

ALLOWED_AUDIO_ASSET_KEYS = {"mp3", "timestamps", "vtt", "chapters", "meta", "manifest"}


class BlogPost(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    slug: str
    title: str
    excerpt: str = ""
    content: str = ""
    category: str = "Reflections"
    cover_image_url: str = ""
    author: str = "The Earnalism"
    pull_quote: str = ""
    is_published: bool = True
    created_at: str = Field(default_factory=now_iso)

class BlogPostIn(BaseModel):
    title: str
    excerpt: str = ""
    content: str = ""
    category: str = "Reflections"
    cover_image_url: str = ""
    author: str = "The Earnalism"
    pull_quote: str = ""
    is_published: bool = True
    slug: Optional[str] = None

class NewsletterIn(BaseModel):
    name: str
    email: EmailStr

class ContactIn(BaseModel):
    name: str
    email: EmailStr
    subject: str = ""
    message: str

class SocialIn(BaseModel):
    instagram: str = ""
    facebook: str = ""
    youtube: str = ""
    linkedin: str = ""
    twitter: str = ""

class BrandIn(BaseModel):
    logo_url: str = ""
    og_image_url: str = ""

class FeaturedIn(BaseModel):
    book_slug: str

class ContactStatusIn(BaseModel):
    status: str  # one of: new, read, responded

VALID_CONTACT_STATUSES = {"new", "read", "responded"}


# ---------- Reader User / Wallet / Session models ----------
class UserSignupIn(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLoginIn(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str = "user"
    reading_seconds_balance: int = 0
    status: str = "active"
    auth_provider: str = "email"
    created_at: str

class UserAuthOut(BaseModel):
    token: str
    user: UserOut

class GoogleAuthIn(BaseModel):
    credential: str

class OTPRequestIn(BaseModel):
    mobile: str

class OTPVerifyIn(BaseModel):
    mobile: str
    otp: str

class WalletAdjustIn(BaseModel):
    minutes: int  # may be negative; converted to seconds server-side
    reason: str = ""

class WalletRefundApproveIn(BaseModel):
    candidate_ids: List[str] = Field(default_factory=list)
    note: str = ""

class WalletTransactionOut(BaseModel):
    id: str
    user_id: str
    type: str  # "credit" | "debit" | "consume"
    seconds: int
    reason: str
    created_at: str
    actor: str = "system"  # "admin" | "system" | "user"
    session_id: str = ""

class ReaderSessionStartIn(BaseModel):
    session_id: Optional[str] = None
    book_id: Optional[str] = None
    book_slug: Optional[str] = None
    chapter_id: Optional[str] = None

class ReaderHeartbeatIn(BaseModel):
    session_id: str
    visible: bool = True
    idle: bool = False
    chapter_id: Optional[str] = None

class ReaderSessionEndIn(BaseModel):
    session_id: str

class ReadingPulseIn(BaseModel):
    session_id: str
    visible: bool = True
    idle: bool = False


class ReadingPassSessionStartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: str = Field(min_length=8, max_length=160)
    device_label: str = Field(default="", max_length=120)
    content_type: Literal["text", "audio"]
    content_id: str = Field(min_length=1, max_length=200)
    canonical_page_index: Optional[int] = Field(default=None, ge=1)
    media_position_seconds: Optional[float] = Field(default=None, ge=0, le=1_000_000_000)


class ReadingPassLeaseRenewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=8, max_length=160)
    lease_version: int = Field(ge=1)
    sequence: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=160)
    active: bool = True
    playback_state: Literal["", "playing", "paused", "buffering", "ended"] = ""


class ReadingPassSessionEndIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=8, max_length=160)
    reason: str = Field(default="user_end", max_length=80)


class ReadingPassPositionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content_type: Literal["text", "audio"]
    content_id: str = Field(min_length=1, max_length=200)
    position: Dict[str, Any] = Field(default_factory=dict)
    version: int = Field(default=0, ge=0)


class ReadingPassSegmentMigrationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    segmentation_version: str = Field(default="canonical-html-blocks-v1", min_length=3, max_length=80)
    target_characters: int = Field(default=3200, ge=800, le=12000)
    activate: bool = False
    dry_run: bool = True


class ReadingPassPreviewActivationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = Field(min_length=3, max_length=120)
    duration_seconds: float = Field(gt=0, le=180)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    bytes: int = Field(gt=0, le=100_000_000)
    store: str = Field(min_length=1, max_length=80)
    bucket: str = Field(min_length=1, max_length=160)
    key: str = Field(min_length=8, max_length=500)
    version_id: str = Field(min_length=1, max_length=240)
    activate: bool = False

class ReaderCompletionIn(BaseModel):
    book_slug: str
    chapter_id: str
    chapter_title: str = ""
    progress: int = 100

class ReaderMetricIn(BaseModel):
    event: str = "reader_metric"
    session_id: str = ""
    book_slug: str = ""
    chapter_id: str = ""
    route: str = ""
    timings: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    tags: Dict[str, Any] = Field(default_factory=dict)

class AnalyticsEventIn(BaseModel):
    event: str = ""
    event_name: str = ""
    route: str = ""
    book_slug: str = ""
    anonymous_session_id: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SecureReaderEventIn(BaseModel):
    session_id: str
    event_type: str
    book_slug: str = ""
    chapter_id: str = ""
    access_token_fingerprint: str = ""
    counts: Dict[str, int] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class UserStatusIn(BaseModel):
    status: str  # "active" | "blocked"


# ---------- Payments / Razorpay top-up models ----------
class PackOut(BaseModel):
    id: str
    label: str
    minutes: int
    price_inr: int
    amount_paise: int
    note: str


class TopUpCreateIn(BaseModel):
    pack_id: str


class TopUpCreateOut(BaseModel):
    intent_id: str
    razorpay_order_id: str
    key_id: str
    amount: int  # in paise
    currency: str = "INR"
    name: str
    description: str
    pack: PackOut
    prefill: dict


class PaymentVerifyIn(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class PaymentReconcileIn(BaseModel):
    note: str = ""
